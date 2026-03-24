"""Replay a workload trace against YAML autoscaling policies."""

import csv
from pathlib import Path

import yaml

from policy_engine import AutoscalingPolicyEngine


BASE_DIR = Path(__file__).resolve().parent


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def action_bucket(action):
    if action.startswith("scale_up"):
        return "scale_up"
    if action.startswith("scale_down"):
        return "scale_down"
    return "hold"


def main():
    config = load_yaml(BASE_DIR / "autoscaling_rules.yaml")["autoscaling"]
    trace_rows = load_rows(BASE_DIR / "workload_metrics.csv")
    engine = AutoscalingPolicyEngine(config)

    output_rows = []
    action_counts = {"scale_up": 0, "scale_down": 0, "hold": 0}
    cooldown_blocks = 0
    first_scale_up_minute = None
    first_scale_down_minute = None
    max_latency = 0.0
    peak_request_ratio = 0.0
    instance_sum = 0.0

    for row in trace_rows:
        minute = int(row["minute"])
        request_rps = float(row["request_rps"])
        cpu_utilization_pct = float(row["cpu_utilization_pct"])
        decision = engine.evaluate(minute, request_rps, cpu_utilization_pct)

        bucket = action_bucket(decision["action"])
        action_counts[bucket] += 1
        cooldown_blocks += int(decision["cooldown_blocked"])
        if bucket == "scale_up" and first_scale_up_minute is None:
            first_scale_up_minute = minute
        if bucket == "scale_down" and first_scale_down_minute is None:
            first_scale_down_minute = minute

        max_latency = max(max_latency, float(decision["projected_latency_ms"]))
        peak_request_ratio = max(peak_request_ratio, float(decision["request_ratio"]))
        instance_sum += float(decision["instance_count"])

        output_rows.append(
            {
                "minute": str(minute),
                "request_rps": f"{request_rps:.0f}",
                "cpu_utilization_pct": f"{cpu_utilization_pct:.0f}",
                "instance_count": str(decision["instance_count"]),
                "action": decision["action"],
                "request_ratio": f"{decision['request_ratio']:.4f}",
                "projected_latency_ms": f"{decision['projected_latency_ms']:.4f}",
                "slo_met": str(bool(decision["slo_met"])).lower(),
                "cooldown_blocked": str(bool(decision["cooldown_blocked"])).lower(),
            }
        )

    with open(BASE_DIR / "autoscaling_results.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "minute",
                "request_rps",
                "cpu_utilization_pct",
                "instance_count",
                "action",
                "request_ratio",
                "projected_latency_ms",
                "slo_met",
                "cooldown_blocked",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    rows_processed = len(output_rows)
    compliance_ratio = sum(row["slo_met"] == "true" for row in output_rows) / rows_processed
    average_instances = instance_sum / rows_processed
    cost = (
        average_instances
        * float(config["service"]["instance_hour_cost_usd"])
        * (rows_processed * float(config["replay"]["dt_minutes"]) / 60.0)
    )

    policy_artifact = {
        "replay": {
            "rows_processed": rows_processed,
            "dt_minutes": int(config["replay"]["dt_minutes"]),
        },
        "service": {
            "name": config["service"]["name"],
            "min_instances": int(config["service"]["min_instances"]),
            "max_instances": int(config["service"]["max_instances"]),
            "initial_instances": int(config["service"]["initial_instances"]),
            "final_instances": int(output_rows[-1]["instance_count"]),
        },
        "policy": {
            "cooldown_steps": {
                "scale_up": int(config["replay"]["cooldown_steps"]["scale_up"]),
                "scale_down": int(config["replay"]["cooldown_steps"]["scale_down"]),
            },
            "scale_up": {
                "request_ratio_threshold": float(config["policies"]["scale_up"]["request_ratio_threshold"]),
                "cpu_threshold_pct": float(config["policies"]["scale_up"]["cpu_threshold_pct"]),
                "latency_threshold_ms": float(config["policies"]["scale_up"]["latency_threshold_ms"]),
                "step": int(config["policies"]["scale_up"]["step"]),
            },
            "scale_down": {
                "request_ratio_threshold": float(config["policies"]["scale_down"]["request_ratio_threshold"]),
                "cpu_threshold_pct": float(config["policies"]["scale_down"]["cpu_threshold_pct"]),
                "latency_threshold_ms": float(config["policies"]["scale_down"]["latency_threshold_ms"]),
                "step": int(config["policies"]["scale_down"]["step"]),
            },
        },
        "results": {
            "actions_taken": action_counts,
            "achieved": {
                "latency_slo_ms": float(config["slo"]["latency_p95_ms"]),
                "compliance_ratio": round(compliance_ratio, 4),
                "max_projected_latency_ms": round(max_latency, 4),
                "average_instances": round(average_instances, 4),
                "estimated_cost_usd": round(cost, 4),
                "cooldown_blocks": int(cooldown_blocks),
                "peak_request_ratio": round(peak_request_ratio, 4),
            },
            "timeline": {
                "first_scale_up_minute": int(first_scale_up_minute),
                "first_scale_down_minute": int(first_scale_down_minute),
            },
        },
        "overall": {
            "target_compliance_ratio_met": compliance_ratio >= float(config["slo"]["compliance_target_ratio"]),
            "constraints_respected": all(
                int(config["service"]["min_instances"]) <= int(row["instance_count"]) <= int(config["service"]["max_instances"])
                for row in output_rows
            ),
        },
    }

    with open(BASE_DIR / "autoscaling_policy.yaml", "w", encoding="utf-8") as handle:
        yaml.dump(policy_artifact, handle, default_flow_style=False, sort_keys=False)

    report = """# Autoscaling Replay Report

## System Design
The replay loads service limits, thresholds, cooldowns, and SLO targets from YAML and evaluates every workload sample with a stateful policy engine.

## Scaling Decisions
The engine scales up when request ratio, CPU, or projected latency exceed the configured scale-up thresholds and scales down only when all scale-down conditions hold and the separate cooldown window has elapsed.

## Replay Results
The replay processed {rows} rows, reached a compliance ratio of {ratio:.2f}, ended with {instances} instances, and observed {blocks} cooldown-blocked decisions.
""".format(
        rows=rows_processed,
        ratio=compliance_ratio,
        instances=output_rows[-1]["instance_count"],
        blocks=cooldown_blocks,
    )

    with open(BASE_DIR / "autoscaling_report.md", "w", encoding="utf-8") as handle:
        handle.write(report)


if __name__ == "__main__":
    main()
