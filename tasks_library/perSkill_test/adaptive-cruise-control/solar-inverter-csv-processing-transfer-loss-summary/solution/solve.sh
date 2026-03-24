#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/inverter_production.csv ]; then
    INPUT_DIR="/root"
    OUTPUT_DIR="/root"
else
    INPUT_DIR="$TASK_DIR/environment"
    OUTPUT_DIR="$TASK_DIR"
fi

INPUT_DIR="$INPUT_DIR" OUTPUT_DIR="$OUTPUT_DIR" python3 <<'PY'
import os
from pathlib import Path

import pandas as pd

input_dir = Path(os.environ["INPUT_DIR"])
output_dir = Path(os.environ["OUTPUT_DIR"])

df = pd.read_csv(input_dir / "inverter_production.csv", na_values=[""])
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["inverter_id", "timestamp"]).reset_index(drop=True)

cause_map = {
    "maint": "planned_maintenance",
    "comms": "communications_outage",
    "grid": "grid_curtailment",
}

rows = []

for inverter_id, group in df.groupby("inverter_id", sort=False):
    group = group.reset_index(drop=True)
    is_valid = group["actual_kwh"].notna() & group["curtailment_flag"].eq("N")
    valid_positions = list(group.index[is_valid])

    idx = 0
    while idx < len(group):
        row = group.iloc[idx]
        is_downtime = pd.isna(row["actual_kwh"]) and row["curtailment_flag"] == "N"
        is_curtailment = pd.notna(row["actual_kwh"]) and row["curtailment_flag"] == "Y"

        if not is_downtime and not is_curtailment:
            idx += 1
            continue

        interval_type = "downtime" if is_downtime else "curtailment"
        start_idx = idx
        event_values = []
        event_code = row["event_code"]

        while idx < len(group):
            current = group.iloc[idx]
            current_is_downtime = pd.isna(current["actual_kwh"]) and current["curtailment_flag"] == "N"
            current_is_curtailment = pd.notna(current["actual_kwh"]) and current["curtailment_flag"] == "Y"
            if interval_type == "downtime" and not current_is_downtime:
                break
            if interval_type == "curtailment" and not current_is_curtailment:
                break
            if pd.notna(current["actual_kwh"]):
                event_values.append(float(current["actual_kwh"]))
            idx += 1

        end_idx = idx - 1

        prev_candidates = [pos for pos in valid_positions if pos < start_idx]
        next_candidates = [pos for pos in valid_positions if pos > end_idx]
        if not prev_candidates or not next_candidates:
            raise ValueError(f"Interval for {inverter_id} lacks neighboring valid samples")

        prev_value = float(group.loc[prev_candidates[-1], "actual_kwh"])
        next_value = float(group.loc[next_candidates[0], "actual_kwh"])
        baseline = (prev_value + next_value) / 2.0
        sample_count = end_idx - start_idx + 1

        if interval_type == "downtime":
            estimated_loss = baseline * sample_count
        else:
            estimated_loss = sum(max(baseline - value, 0.0) for value in event_values)

        rows.append(
            {
                "inverter_id": inverter_id,
                "interval_type": interval_type,
                "interval_start": group.loc[start_idx, "timestamp"].strftime("%Y-%m-%d %H:%M"),
                "interval_end": group.loc[end_idx, "timestamp"].strftime("%Y-%m-%d %H:%M"),
                "sample_count": sample_count,
                "baseline_kwh": round(baseline, 2),
                "estimated_lost_kwh": round(estimated_loss, 2),
                "root_cause_label": cause_map[event_code],
            }
        )

result = pd.DataFrame(
    rows,
    columns=[
        "inverter_id",
        "interval_type",
        "interval_start",
        "interval_end",
        "sample_count",
        "baseline_kwh",
        "estimated_lost_kwh",
        "root_cause_label",
    ],
).sort_values(["inverter_id", "interval_start"]).reset_index(drop=True)

result.to_csv(output_dir / "inverter_loss_summary.csv", index=False)
PY
