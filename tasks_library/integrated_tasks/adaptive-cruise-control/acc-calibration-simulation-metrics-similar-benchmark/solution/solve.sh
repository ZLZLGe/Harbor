#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path("/root")
RUNS_PATH = ROOT / "acc_calibration_runs.csv"
SPEC_PATH = ROOT / "benchmark_spec.yaml"
METRICS_PATH = ROOT / "calibration_metrics.csv"
REPORT_PATH = ROOT / "acc_calibration_benchmark.md"


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

cruise_spec = spec["phases"]["cruise_accel"]
recovery_spec = spec["phases"]["gap_recovery"]
gates = spec["gates"]
normalizers = spec["score_normalizers"]

rows = []
for calibration_id, group in runs.groupby("calibration_id"):
    group = group.sort_values("time_s")

    cruise = group[
        (group["time_s"] >= cruise_spec["start_time_s"])
        & (group["time_s"] <= cruise_spec["end_time_s"])
    ]
    recovery = group[
        (group["time_s"] >= recovery_spec["start_time_s"])
        & (group["time_s"] <= recovery_spec["end_time_s"])
    ]

    recovery_times = recovery["time_s"] - recovery_spec["start_time_s"]

    metrics = {
        "calibration_id": calibration_id,
        "cruise_rise_time_s": rise_time(
            cruise["time_s"].tolist(),
            cruise[cruise_spec["signal_column"]].tolist(),
            cruise_spec["target"],
        ),
        "cruise_overshoot_pct": overshoot_percent(
            cruise[cruise_spec["signal_column"]].tolist(),
            cruise_spec["target"],
        ),
        "cruise_steady_state_error_mps": steady_state_error(
            cruise[cruise_spec["signal_column"]].tolist(),
            cruise_spec["target"],
        ),
        "cruise_settling_time_s": settling_time(
            cruise["time_s"].tolist(),
            cruise[cruise_spec["signal_column"]].tolist(),
            cruise_spec["target"],
            cruise_spec["settling_tolerance"],
        ),
        "recovery_rise_time_s": rise_time(
            recovery_times.tolist(),
            recovery[recovery_spec["signal_column"]].tolist(),
            recovery_spec["target"],
        ),
        "recovery_overshoot_pct": overshoot_percent(
            recovery[recovery_spec["signal_column"]].tolist(),
            recovery_spec["target"],
        ),
        "recovery_steady_state_error_m": steady_state_error(
            recovery[recovery_spec["signal_column"]].tolist(),
            recovery_spec["target"],
        ),
        "recovery_settling_time_s": settling_time(
            recovery_times.tolist(),
            recovery[recovery_spec["signal_column"]].tolist(),
            recovery_spec["target"],
            recovery_spec["settling_tolerance"],
        ),
        "min_distance_m": pd.to_numeric(group["distance_m"], errors="coerce").min(),
    }

    passes_all_gates = (
        metrics["cruise_rise_time_s"] <= gates["cruise_rise_time_max_s"]
        and metrics["cruise_overshoot_pct"] <= gates["cruise_overshoot_max_pct"]
        and metrics["cruise_steady_state_error_mps"] <= gates["cruise_steady_state_error_max_mps"]
        and metrics["cruise_settling_time_s"] <= gates["cruise_settling_time_max_s"]
        and metrics["recovery_rise_time_s"] <= gates["recovery_rise_time_max_s"]
        and metrics["recovery_overshoot_pct"] <= gates["recovery_overshoot_max_pct"]
        and metrics["recovery_steady_state_error_m"] <= gates["recovery_steady_state_error_max_m"]
        and metrics["recovery_settling_time_s"] <= gates["recovery_settling_time_max_s"]
        and metrics["min_distance_m"] >= gates["min_distance_min_m"]
    )

    overall_score = (
        metrics["cruise_rise_time_s"] / normalizers["cruise_rise_time_s"]
        + metrics["cruise_overshoot_pct"] / normalizers["cruise_overshoot_pct"]
        + metrics["cruise_steady_state_error_mps"] / normalizers["cruise_steady_state_error_mps"]
        + metrics["cruise_settling_time_s"] / normalizers["cruise_settling_time_s"]
        + metrics["recovery_rise_time_s"] / normalizers["recovery_rise_time_s"]
        + metrics["recovery_overshoot_pct"] / normalizers["recovery_overshoot_pct"]
        + metrics["recovery_steady_state_error_m"] / normalizers["recovery_steady_state_error_m"]
        + metrics["recovery_settling_time_s"] / normalizers["recovery_settling_time_s"]
    )

    metrics["passes_all_gates"] = "true" if passes_all_gates else "false"
    metrics["overall_score"] = overall_score
    rows.append(metrics)


eligible = [row for row in rows if row["passes_all_gates"] == "true"]
best_id = min(eligible, key=lambda item: item["overall_score"])["calibration_id"]

for row in rows:
    row["recommended"] = "true" if row["calibration_id"] == best_id else "false"

output_columns = [
    "calibration_id",
    "cruise_rise_time_s",
    "cruise_overshoot_pct",
    "cruise_steady_state_error_mps",
    "cruise_settling_time_s",
    "recovery_rise_time_s",
    "recovery_overshoot_pct",
    "recovery_steady_state_error_m",
    "recovery_settling_time_s",
    "min_distance_m",
    "passes_all_gates",
    "overall_score",
    "recommended",
]

metrics_df = pd.DataFrame(rows).sort_values("calibration_id")
for column in output_columns[1:10] + ["overall_score"]:
    metrics_df[column] = metrics_df[column].map(lambda value: round(float(value), 3))
metrics_df = metrics_df[output_columns]
metrics_df.to_csv(METRICS_PATH, index=False)

best_row = metrics_df.loc[metrics_df["recommended"] == "true"].iloc[0]

reasons = {
    "A_comfort": "passes all gates but settles more slowly than the recommended option in both cruise and recovery.",
    "B_aggressive": "is rejected because it exceeds the cruise and recovery overshoot limits and also violates the minimum-distance gate.",
    "C_balanced": "wins because it passes every gate with the lowest overall score.",
    "D_sluggish": "is rejected because both rise-time metrics and both steady-state errors are too large, and its minimum distance is below the gate.",
}

table_columns = output_columns
header_row = "| " + " | ".join(table_columns) + " |"
separator_row = "| " + " | ".join(["---"] * len(table_columns)) + " |"
table_rows = [header_row, separator_row]
for _, row in metrics_df.iterrows():
    table_rows.append("| " + " | ".join(str(row[column]) for column in table_columns) + " |")

report_lines = [
    "# ACC Calibration Benchmark",
    "",
    "## Metric Method",
    "- Cruise metrics use 0.0-30.0 s, target 30.0 m/s, and a +-2% settling band.",
    "- Gap recovery metrics use 40.0-70.0 s, target 45.0 m, a +-5% settling band, and phase-local time referenced to 40.0 s.",
    "- Rise time uses the first 10%-to-90% crossings, overshoot is the percentage above target, steady-state error uses the final 10% average, and settling time is the start of the final uninterrupted in-band interval.",
    "- A calibration is eligible only if it passes every benchmark gate; among eligible candidates, the lowest overall score is recommended.",
    "",
    "## Calibration Summary",
    *table_rows,
    "",
    "## Recommended Calibration",
    (
        f"`{best_row['calibration_id']}` is recommended because it passes every gate and achieves the "
        f"lowest overall score ({best_row['overall_score']:.3f})."
    ),
]

for calibration_id in metrics_df["calibration_id"]:
    report_lines.append(f"- `{calibration_id}` {reasons[calibration_id]}")

REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
PY
