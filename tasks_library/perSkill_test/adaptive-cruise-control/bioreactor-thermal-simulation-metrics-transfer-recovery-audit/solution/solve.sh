#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path
import pandas as pd
import yaml


def base_root() -> Path:
    root = Path("/root")
    try:
        if (root / "thermal_audit_plan.yaml").exists():
            return root
    except PermissionError:
        pass
    return Path.cwd()


def round2(value):
    return round(float(value), 2)


def settling_time(window, target, tolerance, switch_time):
    for idx, row in window.iterrows():
        remaining = window.loc[idx:, "broth_temp_c"]
        if (remaining - target).abs().le(tolerance).all():
            return row["time_min"] - switch_time
    return float("nan")


def overshoot(window, target, direction):
    if direction == "heatup":
        return max(0.0, (window["broth_temp_c"] - target).max())
    return max(0.0, (target - window["broth_temp_c"]).max())


root = base_root()
input_root = root if (root / "thermal_audit_plan.yaml").exists() else root / "environment"
plan_path = input_root / "thermal_audit_plan.yaml"
csv_path = input_root / "reactor_runs" / "batch_bt2403_temperature_trace.csv"
output_path = root / "thermal_recovery_summary.yaml"

with plan_path.open("r", encoding="utf-8") as f:
    plan = yaml.safe_load(f)

trace = pd.read_csv(csv_path)

events_out = []
for event in plan["events"]:
    start, end = event["evaluation_window_min"]
    window = trace[(trace["time_min"] >= start) & (trace["time_min"] <= end)].reset_index(drop=True)
    steady_start = end - float(plan["steady_state_window_min"])
    steady_window = trace[(trace["time_min"] >= steady_start) & (trace["time_min"] <= end)].copy()

    metrics = {
        "overshoot_c": round2(overshoot(window, event["target_setpoint_c"], event["direction"])),
        "settling_time_min": round2(
            settling_time(
                window,
                event["target_setpoint_c"],
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

    events_out.append(
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

worst_event = sorted(
    events_out,
    key=lambda item: (item["pass_count"], -item["metrics"]["overshoot_c"]),
)[0]["event_id"]
largest_overshoot_event = sorted(
    events_out,
    key=lambda item: (-item["metrics"]["overshoot_c"], item["event_id"]),
)[0]["event_id"]

output = {
    "audit": {
        "reactor_id": plan["reactor_id"],
        "batch_id": plan["batch_id"],
        "tolerance_band_c": round2(plan["tolerance_band_c"]),
        "sample_period_min": round2(plan["sample_period_min"]),
    },
    "events": events_out,
    "overall": {
        "passed_events": sum(event["status"] == "pass" for event in events_out),
        "total_events": len(events_out),
        "requires_investigation": any(event["status"] == "fail" for event in events_out),
        "worst_event": worst_event,
        "largest_overshoot_event": largest_overshoot_event,
    },
}

with output_path.open("w", encoding="utf-8") as f:
    yaml.safe_dump(output, f, sort_keys=False, allow_unicode=False)
PY
