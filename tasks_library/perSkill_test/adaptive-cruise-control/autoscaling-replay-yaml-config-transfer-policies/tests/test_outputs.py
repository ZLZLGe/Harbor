"""Tests for the autoscaling replay transfer task."""

import importlib.util
import os
from pathlib import Path

import pandas as pd
import pytest
import yaml


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_latency(config, request_rps, cpu_utilization_pct, instance_count):
    service = config["service"]
    request_ratio = float(request_rps) / (
        float(instance_count) * float(service["capacity_rps_per_instance"])
    )
    overload = max(0.0, request_ratio - 0.7)
    cpu_over = max(0.0, float(cpu_utilization_pct) - 60.0)
    return (
        float(service["base_latency_ms"])
        + overload * float(service["latency_penalty_ms_per_over_capacity"])
        + cpu_over * float(service["cpu_penalty_ms_per_pct_over_60"])
    )


def cooldown_ready(config, minute, direction, last_scale_up_minute, last_scale_down_minute):
    previous = last_scale_up_minute if direction == "scale_up" else last_scale_down_minute
    if previous is None:
        return True
    elapsed_steps = (int(minute) - int(previous)) / int(config["replay"]["dt_minutes"])
    return elapsed_steps >= int(config["replay"]["cooldown_steps"][direction])


def simulate_expected(config, trace):
    service = config["service"]
    policies = config["policies"]
    slo = config["slo"]

    instance_count = int(service["initial_instances"])
    last_scale_up_minute = None
    last_scale_down_minute = None
    output_rows = []

    for row in trace.to_dict("records"):
        minute = int(row["minute"])
        request_rps = float(row["request_rps"])
        cpu_utilization_pct = float(row["cpu_utilization_pct"])

        current_instances = int(instance_count)
        request_ratio = request_rps / (
            current_instances * float(service["capacity_rps_per_instance"])
        )
        projected_latency = project_latency(
            config, request_rps, cpu_utilization_pct, current_instances
        )

        scale_up_signal = (
            request_ratio >= float(policies["scale_up"]["request_ratio_threshold"])
            or cpu_utilization_pct >= float(policies["scale_up"]["cpu_threshold_pct"])
            or projected_latency >= float(policies["scale_up"]["latency_threshold_ms"])
        )
        scale_down_signal = (
            request_ratio <= float(policies["scale_down"]["request_ratio_threshold"])
            and cpu_utilization_pct <= float(policies["scale_down"]["cpu_threshold_pct"])
            and projected_latency <= float(policies["scale_down"]["latency_threshold_ms"])
        )

        action = "hold"
        cooldown_blocked = False

        if scale_up_signal:
            if cooldown_ready(
                config, minute, "scale_up", last_scale_up_minute, last_scale_down_minute
            ):
                target = min(
                    int(service["max_instances"]),
                    current_instances + int(policies["scale_up"]["step"]),
                )
                if target > current_instances:
                    action = f"scale_up_{target - current_instances}"
                    instance_count = target
                    last_scale_up_minute = minute
            else:
                cooldown_blocked = True
        elif scale_down_signal:
            if cooldown_ready(
                config, minute, "scale_down", last_scale_up_minute, last_scale_down_minute
            ):
                target = max(
                    int(service["min_instances"]),
                    current_instances - int(policies["scale_down"]["step"]),
                )
                if target < current_instances:
                    action = f"scale_down_{current_instances - target}"
                    instance_count = target
                    last_scale_down_minute = minute
            else:
                cooldown_blocked = True

        final_instances = int(instance_count)
        final_request_ratio = request_rps / (
            final_instances * float(service["capacity_rps_per_instance"])
        )
        final_projected_latency = project_latency(
            config, request_rps, cpu_utilization_pct, final_instances
        )

        output_rows.append(
            {
                "minute": minute,
                "request_rps": request_rps,
                "cpu_utilization_pct": cpu_utilization_pct,
                "instance_count": final_instances,
                "action": action,
                "request_ratio": final_request_ratio,
                "projected_latency_ms": final_projected_latency,
                "slo_met": final_projected_latency <= float(slo["latency_p95_ms"]),
                "cooldown_blocked": cooldown_blocked,
            }
        )

    return pd.DataFrame(output_rows)


def summarize_expected(config, expected_results):
    action_buckets = expected_results["action"].map(
        lambda action: "scale_up"
        if action.startswith("scale_up")
        else "scale_down"
        if action.startswith("scale_down")
        else "hold"
    )
    rows_processed = len(expected_results)
    compliance_ratio = float(expected_results["slo_met"].mean())
    average_instances = float(expected_results["instance_count"].mean())
    estimated_cost = (
        average_instances
        * float(config["service"]["instance_hour_cost_usd"])
        * (rows_processed * float(config["replay"]["dt_minutes"]) / 60.0)
    )

    def first_minute(bucket):
        matching = expected_results.loc[action_buckets == bucket, "minute"]
        return int(matching.iloc[0]) if not matching.empty else None

    return {
        "actions_taken": {
            "scale_up": int((action_buckets == "scale_up").sum()),
            "scale_down": int((action_buckets == "scale_down").sum()),
            "hold": int((action_buckets == "hold").sum()),
        },
        "achieved": {
            "latency_slo_ms": float(config["slo"]["latency_p95_ms"]),
            "compliance_ratio": round(compliance_ratio, 4),
            "max_projected_latency_ms": round(
                float(expected_results["projected_latency_ms"].max()), 4
            ),
            "average_instances": round(average_instances, 4),
            "estimated_cost_usd": round(estimated_cost, 4),
            "cooldown_blocks": int(expected_results["cooldown_blocked"].sum()),
            "peak_request_ratio": round(
                float(expected_results["request_ratio"].max()), 4
            ),
        },
        "timeline": {
            "first_scale_up_minute": first_minute("scale_up"),
            "first_scale_down_minute": first_minute("scale_down"),
        },
        "overall": {
            "target_compliance_ratio_met": compliance_ratio
            >= float(config["slo"]["compliance_target_ratio"]),
            "constraints_respected": bool(
                expected_results["instance_count"].between(
                    int(config["service"]["min_instances"]),
                    int(config["service"]["max_instances"]),
                ).all()
            ),
        },
    }


class TestInputs:
    def test_input_files(self):
        with open(TASK_ROOT / "autoscaling_rules.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["autoscaling"]

        assert config["replay"]["dt_minutes"] == 5
        assert config["replay"]["duration_minutes"] == 75
        assert config["replay"]["cooldown_steps"]["scale_up"] == 1
        assert config["replay"]["cooldown_steps"]["scale_down"] == 2
        assert config["service"]["name"] == "checkout-api"
        assert config["service"]["min_instances"] == 2
        assert config["service"]["max_instances"] == 6
        assert config["slo"]["latency_p95_ms"] == 180
        assert config["slo"]["compliance_target_ratio"] == 0.8

        trace = pd.read_csv(TASK_ROOT / "workload_metrics.csv")
        assert len(trace) == 16
        assert list(trace.columns) == ["minute", "request_rps", "cpu_utilization_pct"]
        assert trace["minute"].iloc[0] == 0
        assert trace["minute"].iloc[-1] == 75


class TestPolicyEngine:
    def test_engine_interface(self):
        module = load_module("policy_engine", TASK_ROOT / "policy_engine.py")
        with open(TASK_ROOT / "autoscaling_rules.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["autoscaling"]

        assert hasattr(module, "AutoscalingPolicyEngine")
        engine = module.AutoscalingPolicyEngine(config)
        engine.reset()

        initial = engine.evaluate(minute=0, request_rps=120, cpu_utilization_pct=42)
        assert set(initial.keys()) == {
            "action",
            "instance_count",
            "request_ratio",
            "projected_latency_ms",
            "slo_met",
            "cooldown_blocked",
        }
        assert initial["action"] == "hold"
        assert initial["instance_count"] == 2

        surge = engine.evaluate(minute=10, request_rps=175, cpu_utilization_pct=63)
        assert surge["action"].startswith("scale_up")
        assert surge["instance_count"] == 4
        assert surge["projected_latency_ms"] == pytest.approx(
            project_latency(config, 175, 63, 4), abs=1e-4
        )


class TestReplayOutputs:
    def test_results_csv(self):
        with open(TASK_ROOT / "autoscaling_rules.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["autoscaling"]
        trace = pd.read_csv(TASK_ROOT / "workload_metrics.csv")
        results = pd.read_csv(TASK_ROOT / "autoscaling_results.csv")
        expected = simulate_expected(config, trace)

        assert list(results.columns) == [
            "minute",
            "request_rps",
            "cpu_utilization_pct",
            "instance_count",
            "action",
            "request_ratio",
            "projected_latency_ms",
            "slo_met",
            "cooldown_blocked",
        ]
        assert len(results) == len(trace)
        assert results["instance_count"].between(2, 6).all()
        assert list(results["minute"]) == expected["minute"].tolist()
        assert list(results["action"]) == expected["action"].tolist()
        assert results["instance_count"].tolist() == expected["instance_count"].tolist()
        assert results["slo_met"].astype(str).str.lower().map(
            {"true": True, "false": False}
        ).tolist() == expected["slo_met"].tolist()
        assert results["cooldown_blocked"].astype(str).str.lower().map(
            {"true": True, "false": False}
        ).tolist() == expected["cooldown_blocked"].tolist()

        for column in ["request_ratio", "projected_latency_ms"]:
            assert results[column].astype(float).tolist() == pytest.approx(
                expected[column].astype(float).tolist(),
                abs=1e-4,
            )

    def test_policy_yaml(self):
        with open(TASK_ROOT / "autoscaling_policy.yaml", "r", encoding="utf-8") as handle:
            artifact = yaml.safe_load(handle)
        with open(TASK_ROOT / "autoscaling_rules.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["autoscaling"]
        trace = pd.read_csv(TASK_ROOT / "workload_metrics.csv")
        expected_results = simulate_expected(config, trace)
        expected_summary = summarize_expected(config, expected_results)

        assert artifact["replay"]["rows_processed"] == 16
        assert artifact["replay"]["dt_minutes"] == 5
        assert artifact["service"]["name"] == config["service"]["name"]
        assert artifact["service"]["initial_instances"] == 2
        assert artifact["service"]["final_instances"] == int(
            expected_results["instance_count"].iloc[-1]
        )
        assert artifact["policy"]["cooldown_steps"]["scale_up"] == 1
        assert artifact["policy"]["cooldown_steps"]["scale_down"] == 2
        assert artifact["policy"]["scale_up"]["request_ratio_threshold"] == 0.82
        assert artifact["policy"]["scale_down"]["step"] == 1

        achieved = artifact["results"]["achieved"]
        assert artifact["results"]["actions_taken"] == expected_summary["actions_taken"]
        assert achieved["latency_slo_ms"] == expected_summary["achieved"]["latency_slo_ms"]
        assert achieved["compliance_ratio"] == pytest.approx(
            expected_summary["achieved"]["compliance_ratio"], abs=1e-4
        )
        assert achieved["max_projected_latency_ms"] == pytest.approx(
            expected_summary["achieved"]["max_projected_latency_ms"], abs=1e-4
        )
        assert achieved["average_instances"] == pytest.approx(
            expected_summary["achieved"]["average_instances"], abs=1e-4
        )
        assert achieved["estimated_cost_usd"] == pytest.approx(
            expected_summary["achieved"]["estimated_cost_usd"], abs=1e-4
        )
        assert achieved["cooldown_blocks"] == expected_summary["achieved"]["cooldown_blocks"]
        assert achieved["peak_request_ratio"] == pytest.approx(
            expected_summary["achieved"]["peak_request_ratio"], abs=1e-4
        )

        timeline = artifact["results"]["timeline"]
        assert timeline == expected_summary["timeline"]
        assert artifact["overall"] == expected_summary["overall"]

    def test_report_sections(self):
        content = (TASK_ROOT / "autoscaling_report.md").read_text(encoding="utf-8").lower()
        assert "system design" in content
        assert "scaling decisions" in content
        assert "replay results" in content
