#!/bin/bash
set -euo pipefail

python3 <<'PY'
import os
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
RUNS_PATH = ROOT / "robotic_joint_runs.csv"
SPEC_PATH = ROOT / "validation_spec.yaml"
OUTPUT_PATH = ROOT / "robotic_joint_validation.yaml"


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


def round_metrics(metrics):
    return {key: round(float(value), 3) for key, value in metrics.items()}


with SPEC_PATH.open("r", encoding="utf-8") as handle:
    spec = yaml.safe_load(handle)

runs = pd.read_csv(RUNS_PATH)
target_angle = float(spec["target_angle_deg"])
step_spec = spec["phases"]["step_response"]
load_spec = spec["phases"]["load_recovery"]
gates = spec["gates"]
normalizers = spec["score_normalizers"]

controller_rows = []
failure_reasons = {}

for controller_id, group in runs.groupby("controller_id"):
    group = group.sort_values("time_s")

    step = group[
        (group["time_s"] >= step_spec["start_time_s"])
        & (group["time_s"] <= step_spec["end_time_s"])
    ]
    load = group[
        (group["time_s"] >= load_spec["start_time_s"])
        & (group["time_s"] <= load_spec["end_time_s"])
    ].copy()

    recovery_origin = float(load.iloc[0][load_spec["signal_column"]])
    recovery_target = target_angle - recovery_origin
    load["recovery_signal_deg"] = load[load_spec["signal_column"]] - recovery_origin
    load_times = load["time_s"] - load_spec["start_time_s"]

    step_metrics = {
        "rise_time_s": rise_time(
            step["time_s"].tolist(),
            step[step_spec["signal_column"]].tolist(),
            float(step_spec["target"]),
        ),
        "overshoot_pct": overshoot_percent(
            step[step_spec["signal_column"]].tolist(),
            float(step_spec["target"]),
        ),
        "settling_time_s": settling_time(
            step["time_s"].tolist(),
            step[step_spec["signal_column"]].tolist(),
            float(step_spec["target"]),
            float(step_spec["settling_tolerance"]),
        ),
        "steady_state_error_deg": steady_state_error(
            step[step_spec["signal_column"]].tolist(),
            float(step_spec["target"]),
            float(step_spec["steady_state_fraction"]),
        ),
    }

    load_metrics = {
        "rise_time_s": rise_time(
            load_times.tolist(),
            load["recovery_signal_deg"].tolist(),
            recovery_target,
        ),
        "overshoot_pct": overshoot_percent(
            load["recovery_signal_deg"].tolist(),
            recovery_target,
        ),
        "settling_time_s": settling_time(
            load_times.tolist(),
            load["recovery_signal_deg"].tolist(),
            recovery_target,
            float(load_spec["settling_tolerance"]),
        ),
        "steady_state_error_deg": steady_state_error(
            load["recovery_signal_deg"].tolist(),
            recovery_target,
            float(load_spec["steady_state_fraction"]),
        ),
    }

    gate_checks = {
        "step rise time": step_metrics["rise_time_s"] <= gates["step_rise_time_max_s"],
        "step overshoot": step_metrics["overshoot_pct"] <= gates["step_overshoot_max_pct"],
        "step settling time": step_metrics["settling_time_s"] <= gates["step_settling_time_max_s"],
        "step steady-state error": step_metrics["steady_state_error_deg"] <= gates["step_steady_state_error_max_deg"],
        "load rise time": load_metrics["rise_time_s"] <= gates["load_rise_time_max_s"],
        "load overshoot": load_metrics["overshoot_pct"] <= gates["load_overshoot_max_pct"],
        "load settling time": load_metrics["settling_time_s"] <= gates["load_settling_time_max_s"],
        "load steady-state error": load_metrics["steady_state_error_deg"] <= gates["load_steady_state_error_max_deg"],
    }

    overall_score = (
        step_metrics["rise_time_s"] / normalizers["step_rise_time_s"]
        + step_metrics["overshoot_pct"] / normalizers["step_overshoot_pct"]
        + step_metrics["settling_time_s"] / normalizers["step_settling_time_s"]
        + step_metrics["steady_state_error_deg"] / normalizers["step_steady_state_error_deg"]
        + load_metrics["rise_time_s"] / normalizers["load_rise_time_s"]
        + load_metrics["overshoot_pct"] / normalizers["load_overshoot_pct"]
        + load_metrics["settling_time_s"] / normalizers["load_settling_time_s"]
        + load_metrics["steady_state_error_deg"] / normalizers["load_steady_state_error_deg"]
    )

    passes_acceptance = all(gate_checks.values())
    failure_reasons[controller_id] = [
        name for name, passed in gate_checks.items() if not passed
    ]

    controller_rows.append(
        {
            "controller_id": controller_id,
            "passes_acceptance": passes_acceptance,
            "overall_score_raw": overall_score,
            "step_response": round_metrics(step_metrics),
            "load_recovery": round_metrics(load_metrics),
        }
    )

controller_rows.sort(
    key=lambda row: (
        0 if row["passes_acceptance"] else 1,
        row["overall_score_raw"],
        row["controller_id"],
    )
)

for index, row in enumerate(controller_rows, start=1):
    row["rank"] = index
    row["overall_score"] = round(float(row.pop("overall_score_raw")), 3)

recommended_controller_id = controller_rows[0]["controller_id"]
accepted_controllers = [
    row["controller_id"] for row in controller_rows if row["passes_acceptance"]
]
rejected_controllers = [
    row["controller_id"] for row in controller_rows if not row["passes_acceptance"]
]

summary_bits = [
    f"{recommended_controller_id} is recommended because it passes every acceptance gate and has the lowest overall score."
]
for row in controller_rows:
    controller_id = row["controller_id"]
    if controller_id == recommended_controller_id:
        continue
    if row["passes_acceptance"]:
        summary_bits.append(
            f"{controller_id} also passes but ranks lower because its overall score is higher."
        )
    else:
        failed = ", ".join(failure_reasons[controller_id])
        summary_bits.append(
            f"{controller_id} is rejected because it fails these checks: {failed}."
        )

output = {
    "recommended_controller_id": recommended_controller_id,
    "controllers": [
        {
            "controller_id": row["controller_id"],
            "rank": row["rank"],
            "passes_acceptance": row["passes_acceptance"],
            "overall_score": row["overall_score"],
            "step_response": row["step_response"],
            "load_recovery": row["load_recovery"],
        }
        for row in controller_rows
    ],
    "acceptance_summary": {
        "accepted_controllers": accepted_controllers,
        "rejected_controllers": rejected_controllers,
        "conclusion": " ".join(summary_bits),
    },
}

with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
    yaml.safe_dump(output, handle, sort_keys=False, allow_unicode=False)
PY
