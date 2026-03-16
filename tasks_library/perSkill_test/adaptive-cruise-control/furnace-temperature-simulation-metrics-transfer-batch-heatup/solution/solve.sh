#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path("/root")
RUNS_PATH = ROOT / "furnace_temperature_runs.csv"
SPEC_PATH = ROOT / "furnace_benchmark.yaml"
METRICS_PATH = ROOT / "furnace_metrics.csv"
REPORT_PATH = ROOT / "furnace_temperature_report.md"


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


def steady_state_error(values, target, final_fraction=0.1):
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


with SPEC_PATH.open("r", encoding="utf-8") as handle:
    spec = yaml.safe_load(handle)

runs = pd.read_csv(RUNS_PATH)
target_temperature = spec["target_temperature_c"]
heatup_spec = spec["phases"]["heatup"]
recovery_spec = spec["phases"]["recovery"]
gates = spec["gates"]
normalizers = spec["score_normalizers"]

rows = []
failure_reasons = {}
for configuration_id, group in runs.groupby("configuration_id"):
    group = group.sort_values("time_min")

    heatup = group[
        (group["time_min"] >= heatup_spec["start_time_min"])
        & (group["time_min"] <= heatup_spec["end_time_min"])
    ]
    recovery = group[
        (group["time_min"] >= recovery_spec["start_time_min"])
        & (group["time_min"] <= recovery_spec["end_time_min"])
    ]

    recovery_floor = recovery["temperature_c"].min()
    recovery_target = target_temperature - recovery_floor
    recovery_progress = recovery["temperature_c"] - recovery_floor
    recovery_times = recovery["time_min"] - recovery_spec["start_time_min"]

    metrics = {
        "configuration_id": configuration_id,
        "heatup_rise_time_min": rise_time(
            heatup["time_min"].tolist(),
            heatup["temperature_c"].tolist(),
            target_temperature,
        ),
        "heatup_overshoot_pct": overshoot_percent(
            heatup["temperature_c"].tolist(),
            target_temperature,
        ),
        "heatup_steady_state_error_c": steady_state_error(
            heatup["temperature_c"].tolist(),
            target_temperature,
        ),
        "heatup_settling_time_min": settling_time(
            heatup["time_min"].tolist(),
            heatup["temperature_c"].tolist(),
            target_temperature,
            heatup_spec["settling_tolerance"],
        ),
        "recovery_floor_c": recovery_floor,
        "recovery_rise_time_min": rise_time(
            recovery_times.tolist(),
            recovery_progress.tolist(),
            recovery_target,
        ),
        "recovery_overshoot_pct": overshoot_percent(
            recovery_progress.tolist(),
            recovery_target,
        ),
        "recovery_steady_state_error_c": steady_state_error(
            recovery_progress.tolist(),
            recovery_target,
        ),
        "recovery_settling_time_min": settling_time(
            recovery_times.tolist(),
            recovery_progress.tolist(),
            recovery_target,
            recovery_spec["settling_tolerance"],
        ),
    }

    gate_checks = {
        "heat-up rise time": metrics["heatup_rise_time_min"] <= gates["heatup_rise_time_max_min"],
        "heat-up overshoot": metrics["heatup_overshoot_pct"] <= gates["heatup_overshoot_max_pct"],
        "heat-up steady-state error": metrics["heatup_steady_state_error_c"] <= gates["heatup_steady_state_error_max_c"],
        "heat-up settling time": metrics["heatup_settling_time_min"] <= gates["heatup_settling_time_max_min"],
        "recovery floor": metrics["recovery_floor_c"] >= gates["recovery_floor_min_c"],
        "recovery rise time": metrics["recovery_rise_time_min"] <= gates["recovery_rise_time_max_min"],
        "recovery overshoot": metrics["recovery_overshoot_pct"] <= gates["recovery_overshoot_max_pct"],
        "recovery steady-state error": metrics["recovery_steady_state_error_c"] <= gates["recovery_steady_state_error_max_c"],
        "recovery settling time": metrics["recovery_settling_time_min"] <= gates["recovery_settling_time_max_min"],
    }

    metrics["passes_all_gates"] = "true" if all(gate_checks.values()) else "false"
    metrics["overall_score"] = (
        metrics["heatup_rise_time_min"] / normalizers["heatup_rise_time_min"]
        + metrics["heatup_overshoot_pct"] / normalizers["heatup_overshoot_pct"]
        + metrics["heatup_steady_state_error_c"] / normalizers["heatup_steady_state_error_c"]
        + metrics["heatup_settling_time_min"] / normalizers["heatup_settling_time_min"]
        + metrics["recovery_rise_time_min"] / normalizers["recovery_rise_time_min"]
        + metrics["recovery_overshoot_pct"] / normalizers["recovery_overshoot_pct"]
        + metrics["recovery_steady_state_error_c"] / normalizers["recovery_steady_state_error_c"]
        + metrics["recovery_settling_time_min"] / normalizers["recovery_settling_time_min"]
    )

    failed = [name for name, passed in gate_checks.items() if not passed]
    failure_reasons[configuration_id] = failed
    rows.append(metrics)


eligible = [row for row in rows if row["passes_all_gates"] == "true"]
best_id = min(eligible, key=lambda item: item["overall_score"])["configuration_id"]

for row in rows:
    row["recommended"] = "true" if row["configuration_id"] == best_id else "false"

output_columns = [
    "configuration_id",
    "heatup_rise_time_min",
    "heatup_overshoot_pct",
    "heatup_steady_state_error_c",
    "heatup_settling_time_min",
    "recovery_floor_c",
    "recovery_rise_time_min",
    "recovery_overshoot_pct",
    "recovery_steady_state_error_c",
    "recovery_settling_time_min",
    "passes_all_gates",
    "overall_score",
    "recommended",
]

metrics_df = pd.DataFrame(rows).sort_values("configuration_id")
for column in output_columns[1:10] + ["overall_score"]:
    metrics_df[column] = metrics_df[column].map(lambda value: round(float(value), 3))
metrics_df = metrics_df[output_columns]
metrics_df.to_csv(METRICS_PATH, index=False)

table_header = "| " + " | ".join(output_columns) + " |"
table_divider = "| " + " | ".join(["---"] * len(output_columns)) + " |"
table_rows = [table_header, table_divider]
for _, row in metrics_df.iterrows():
    table_rows.append("| " + " | ".join(str(row[column]) for column in output_columns) + " |")

report_lines = [
    "# Industrial Furnace Temperature Report",
    "",
    "## Metric Method",
    "- Heat-up metrics use 0.0-80.0 min, the raw `temperature_c` signal, a target of 850.0 C, and a +-1.5% settling band.",
    "- Recovery metrics use 90.0-140.0 min, define `recovery_floor_c` as the minimum furnace temperature in that window, and analyze `recovery_progress_c = temperature_c - recovery_floor_c` against `recovery_target_c = 850.0 - recovery_floor_c` with phase-local time referenced to 90.0 min.",
    "- Rise time uses the first 10%-to-90% crossings, overshoot is the percentage above target, steady-state error uses the final 10% average, and settling time is the start of the final uninterrupted in-band interval.",
    "- A configuration is eligible only if it passes every acceptance gate; among eligible configurations, the lowest overall score is recommended.",
    "",
    "## Configuration Summary",
    *table_rows,
    "",
    "## Recommended Configuration",
]

best_row = metrics_df.loc[metrics_df["recommended"] == "true"].iloc[0]
report_lines.append(
    f"`{best_row['configuration_id']}` is recommended because it passes every gate and achieves the lowest overall score ({best_row['overall_score']:.3f})."
)

for _, row in metrics_df.iterrows():
    configuration_id = row["configuration_id"]
    if configuration_id == best_id:
        report_lines.append(
            f"- `{configuration_id}` is the most robust option: it clears all heat-up and recovery gates while keeping the combined score lowest."
        )
    elif row["passes_all_gates"] == "true":
        report_lines.append(
            f"- `{configuration_id}` passes all gates but is not selected because its overall score is higher than `{best_id}`."
        )
    else:
        failed = ", ".join(failure_reasons[configuration_id])
        report_lines.append(
            f"- `{configuration_id}` is not selected because it fails the following gate checks: {failed}."
        )

REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
PY
