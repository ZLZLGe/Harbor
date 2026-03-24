from pathlib import Path

import pandas as pd
import yaml


def task_root():
    root = Path("/root")
    try:
        if (root / "thermal_audit_plan.yaml").exists():
            return root
    except PermissionError:
        pass
    return Path(__file__).resolve().parents[1]


ROOT = task_root()
INPUT_ROOT = ROOT if (ROOT / "thermal_audit_plan.yaml").exists() else ROOT / "environment"
PLAN_PATH = INPUT_ROOT / "thermal_audit_plan.yaml"
TRACE_PATH = INPUT_ROOT / "reactor_runs" / "batch_bt2403_temperature_trace.csv"
OUTPUT_PATH = ROOT / "thermal_recovery_summary.yaml"


def round2(value):
    return round(float(value), 2)


def event_window(df, bounds):
    start, end = bounds
    return df[(df["time_min"] >= start) & (df["time_min"] <= end)].reset_index(drop=True)


def calc_overshoot(window, target, direction):
    if direction == "heatup":
        return max(0.0, (window["broth_temp_c"] - target).max())
    return max(0.0, (target - window["broth_temp_c"]).max())


def calc_settling(window, target, tolerance, switch_time):
    for idx, row in window.iterrows():
        if (window.loc[idx:, "broth_temp_c"] - target).abs().le(tolerance).all():
            return row["time_min"] - switch_time
    raise AssertionError("No settling time found inside evaluation window")


def expected_output():
    with PLAN_PATH.open("r", encoding="utf-8") as f:
        plan = yaml.safe_load(f)
    trace = pd.read_csv(TRACE_PATH)

    events = []
    for event in plan["events"]:
        window = event_window(trace, event["evaluation_window_min"])
        end = float(event["evaluation_window_min"][1])
        steady_start = end - float(plan["steady_state_window_min"])
        steady_window = trace[(trace["time_min"] >= steady_start) & (trace["time_min"] <= end)]

        metrics = {
            "overshoot_c": round2(calc_overshoot(window, event["target_setpoint_c"], event["direction"])),
            "settling_time_min": round2(
                calc_settling(
                    window,
                    float(event["target_setpoint_c"]),
                    float(plan["tolerance_band_c"]),
                    float(event["switch_time_min"]),
                )
            ),
            "steady_state_error_c": round2(
                abs(steady_window["broth_temp_c"].mean() - float(event["target_setpoint_c"]))
            ),
            "out_of_tolerance_duration_min": round2(
                ((window["broth_temp_c"] - float(event["target_setpoint_c"])).abs() > float(plan["tolerance_band_c"])).sum()
                * float(plan["sample_period_min"])
            ),
        }
        limits = {
            "overshoot_c_max": round2(event["limits"]["overshoot_c_max"]),
            "settling_time_min_max": round2(event["limits"]["settling_time_min_max"]),
            "steady_state_error_c_max": round2(event["limits"]["steady_state_error_c_max"]),
            "out_of_tolerance_duration_min_max": round2(event["limits"]["out_of_tolerance_duration_min_max"]),
        }
        pass_count = sum(
            [
                metrics["overshoot_c"] <= limits["overshoot_c_max"],
                metrics["settling_time_min"] <= limits["settling_time_min_max"],
                metrics["steady_state_error_c"] <= limits["steady_state_error_c_max"],
                metrics["out_of_tolerance_duration_min"] <= limits["out_of_tolerance_duration_min_max"],
            ]
        )
        events.append(
            {
                "event_id": event["event_id"],
                "phase": event["phase"],
                "direction": event["direction"],
                "switch_time_min": round2(event["switch_time_min"]),
                "target_setpoint_c": round2(event["target_setpoint_c"]),
                "metrics": metrics,
                "limits": limits,
                "pass_count": int(pass_count),
                "status": "pass" if pass_count == 4 else "fail",
            }
        )

    worst_event = sorted(events, key=lambda item: (item["pass_count"], -item["metrics"]["overshoot_c"]))[0]["event_id"]
    largest_overshoot_event = sorted(
        events, key=lambda item: (-item["metrics"]["overshoot_c"], item["event_id"])
    )[0]["event_id"]

    return {
        "audit": {
            "reactor_id": plan["reactor_id"],
            "batch_id": plan["batch_id"],
            "tolerance_band_c": round2(plan["tolerance_band_c"]),
            "sample_period_min": round2(plan["sample_period_min"]),
        },
        "events": events,
        "overall": {
            "passed_events": sum(event["status"] == "pass" for event in events),
            "total_events": len(events),
            "requires_investigation": any(event["status"] == "fail" for event in events),
            "worst_event": worst_event,
            "largest_overshoot_event": largest_overshoot_event,
        },
    }


def test_assets_present():
    assert PLAN_PATH.exists(), "thermal_audit_plan.yaml is missing"
    assert TRACE_PATH.exists(), "batch_bt2403_temperature_trace.csv is missing"
    assert OUTPUT_PATH.exists(), "thermal_recovery_summary.yaml is missing"

    trace = pd.read_csv(TRACE_PATH)
    assert len(trace) == 101
    assert list(trace.columns) == [
        "time_min",
        "setpoint_c",
        "broth_temp_c",
        "jacket_temp_c",
        "steam_valve_pct",
        "phase",
    ]
    assert trace["time_min"].iloc[0] == 0
    assert trace["time_min"].iloc[-1] == 100


def test_output_structure():
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert list(data.keys()) == ["audit", "events", "overall"]
    assert set(data["audit"].keys()) == {
        "reactor_id",
        "batch_id",
        "tolerance_band_c",
        "sample_period_min",
    }
    assert isinstance(data["events"], list)
    assert len(data["events"]) == 2
    assert set(data["overall"].keys()) == {
        "passed_events",
        "total_events",
        "requires_investigation",
        "worst_event",
        "largest_overshoot_event",
    }


def test_metrics_and_overall_match_inputs():
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        actual = yaml.safe_load(f)

    expected = expected_output()
    assert actual == expected


def test_expected_audit_result_is_recovery_investigation():
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["events"][0]["event_id"] == "nutrient_shift_heatup"
    assert data["events"][0]["status"] == "pass"
    assert data["events"][0]["pass_count"] == 4
    assert data["events"][0]["metrics"] == {
        "overshoot_c": 0.32,
        "settling_time_min": 15.0,
        "steady_state_error_c": 0.0,
        "out_of_tolerance_duration_min": 10.0,
    }

    assert data["events"][1]["event_id"] == "induction_coolback"
    assert data["events"][1]["status"] == "fail"
    assert data["events"][1]["pass_count"] == 1
    assert data["events"][1]["metrics"] == {
        "overshoot_c": 0.4,
        "settling_time_min": 14.0,
        "steady_state_error_c": 0.01,
        "out_of_tolerance_duration_min": 10.0,
    }

    assert data["overall"] == {
        "passed_events": 1,
        "total_events": 2,
        "requires_investigation": True,
        "worst_event": "induction_coolback",
        "largest_overshoot_event": "induction_coolback",
    }
