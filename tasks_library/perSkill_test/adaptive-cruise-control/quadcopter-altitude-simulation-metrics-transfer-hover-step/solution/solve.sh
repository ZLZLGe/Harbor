#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path("/root")
RUNS_PATH = ROOT / "quadcopter_altitude_runs.csv"
SPEC_PATH = ROOT / "scorecard_spec.yaml"
OUTPUT_PATH = ROOT / "quadcopter_altitude_scorecard.json"


def rise_time(times, values, target):
    t10 = None
    t90 = None
    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = float(t)
        if t90 is None and v >= 0.9 * target:
            t90 = float(t)
            break
    if t10 is None or t90 is None:
        return None
    return t90 - t10


def overshoot_percent(values, target):
    maximum = max(values)
    if maximum <= target:
        return 0.0
    return ((maximum - target) / target) * 100.0


def steady_state_error(values, target, final_fraction):
    start = int(len(values) * (1.0 - final_fraction))
    final_slice = values[start:]
    final_average = sum(final_slice) / len(final_slice)
    return abs(target - final_average)


def settling_time(times, values, target, tolerance):
    band = target * tolerance
    lower = target - band
    upper = target + band
    settled_at = None
    for t, v in zip(times, values):
        if v < lower or v > upper:
            settled_at = None
        elif settled_at is None:
            settled_at = float(t)
    return settled_at


def rounded_metrics(metrics):
    return {key: round(float(value), 3) for key, value in metrics.items()}


with SPEC_PATH.open("r", encoding="utf-8") as handle:
    spec = yaml.safe_load(handle)

runs = pd.read_csv(RUNS_PATH)
climb_spec = spec["phases"]["climb_step"]
recovery_spec = spec["phases"]["gust_recovery"]
limits = spec["limits"]
normalizers = spec["score_normalizers"]
hold_target = float(spec["targets"]["hold_altitude_m"])

controller_rows = []
for controller_id, group in runs.groupby("controller_id"):
    group = group.sort_values("time_s")

    climb = group[
        (group["time_s"] >= climb_spec["start_time_s"])
        & (group["time_s"] <= climb_spec["end_time_s"])
    ]
    recovery = group[
        (group["time_s"] >= recovery_spec["start_time_s"])
        & (group["time_s"] <= recovery_spec["end_time_s"])
    ].copy()

    recovery_origin = float(recovery.iloc[0][recovery_spec["signal_column"]])
    recovery_target = hold_target - recovery_origin
    recovery["recovery_signal_m"] = recovery[recovery_spec["signal_column"]] - recovery_origin
    recovery_times = recovery["time_s"] - recovery_spec["start_time_s"]

    climb_metrics = {
        "rise_time_s": rise_time(
            climb["time_s"].tolist(),
            climb[climb_spec["signal_column"]].tolist(),
            float(climb_spec["target"]),
        ),
        "overshoot_pct": overshoot_percent(
            climb[climb_spec["signal_column"]].tolist(),
            float(climb_spec["target"]),
        ),
        "settling_time_s": settling_time(
            climb["time_s"].tolist(),
            climb[climb_spec["signal_column"]].tolist(),
            float(climb_spec["target"]),
            float(climb_spec["settling_tolerance"]),
        ),
        "steady_state_error_m": steady_state_error(
            climb[climb_spec["signal_column"]].tolist(),
            float(climb_spec["target"]),
            float(climb_spec["steady_state_fraction"]),
        ),
    }

    recovery_metrics = {
        "rise_time_s": rise_time(
            recovery_times.tolist(),
            recovery["recovery_signal_m"].tolist(),
            recovery_target,
        ),
        "overshoot_pct": overshoot_percent(
            recovery["recovery_signal_m"].tolist(),
            recovery_target,
        ),
        "settling_time_s": settling_time(
            recovery_times.tolist(),
            recovery["recovery_signal_m"].tolist(),
            recovery_target,
            float(recovery_spec["settling_tolerance"]),
        ),
        "steady_state_error_m": steady_state_error(
            recovery["recovery_signal_m"].tolist(),
            recovery_target,
            float(recovery_spec["steady_state_fraction"]),
        ),
    }

    score_inputs = {
        "climb_rise_time_s": climb_metrics["rise_time_s"],
        "climb_overshoot_pct": climb_metrics["overshoot_pct"],
        "climb_settling_time_s": climb_metrics["settling_time_s"],
        "climb_steady_state_error_m": climb_metrics["steady_state_error_m"],
        "recovery_rise_time_s": recovery_metrics["rise_time_s"],
        "recovery_overshoot_pct": recovery_metrics["overshoot_pct"],
        "recovery_settling_time_s": recovery_metrics["settling_time_s"],
        "recovery_steady_state_error_m": recovery_metrics["steady_state_error_m"],
    }
    passes = all(score_inputs[key] <= float(limits[key]) for key in score_inputs)
    overall_score = sum(score_inputs[key] / float(normalizers[key]) for key in score_inputs)

    controller_rows.append(
        {
            "controller_id": controller_id,
            "passes_all_limits": passes,
            "overall_score": overall_score,
            "climb_step": rounded_metrics(climb_metrics),
            "gust_recovery": rounded_metrics(recovery_metrics),
        }
    )

controller_rows.sort(
    key=lambda row: (
        0 if row["passes_all_limits"] else 1,
        row["overall_score"],
        row["controller_id"],
    )
)

for index, row in enumerate(controller_rows, start=1):
    row["rank"] = index
    row["overall_score"] = round(float(row["overall_score"]), 3)

best_controller_id = controller_rows[0]["controller_id"]
passes = [row["controller_id"] for row in controller_rows if row["passes_all_limits"]]
fails = [row["controller_id"] for row in controller_rows if not row["passes_all_limits"]]

summary_parts = [
    f"{best_controller_id} wins because it passes every limit with the lowest overall score."
]
if len(passes) > 1:
    others = [controller_id for controller_id in passes if controller_id != best_controller_id]
    summary_parts.append(
        f"{', '.join(others)} also pass but rank lower because their overall scores are higher."
    )
if fails:
    summary_parts.append(
        f"{', '.join(fails)} are not selected because they miss one or more overshoot limits."
    )

output = {
    "best_controller_id": best_controller_id,
    "controllers": controller_rows,
    "recommendation_summary": " ".join(summary_parts),
}

OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
PY
