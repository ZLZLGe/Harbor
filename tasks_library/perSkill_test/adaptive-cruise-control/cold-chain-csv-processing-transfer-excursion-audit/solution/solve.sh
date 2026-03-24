#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/shipment_temperature_log.csv ] && [ -f /root/shipment_thresholds.csv ]; then
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

thresholds = pd.read_csv(input_dir / "shipment_thresholds.csv")
logs = pd.read_csv(input_dir / "shipment_temperature_log.csv", na_values=[""])
logs["timestamp"] = pd.to_datetime(logs["timestamp"])

merged = logs.merge(thresholds, on="shipment_id", how="left")
merged = merged.sort_values(["shipment_id", "timestamp"]).reset_index(drop=True)

results = []

for shipment_id, group in merged.groupby("shipment_id", sort=False):
    current = None

    for row in group.itertuples(index=False):
        temp = row.temperature_c
        is_missing = pd.isna(temp)
        is_breach = (not is_missing) and temp > row.max_allowed_temp_c

        if is_breach:
            if current is None:
                current = {
                    "shipment_id": shipment_id,
                    "start": row.timestamp,
                    "end": row.timestamp,
                    "peak": float(temp),
                    "door_open": row.door_open == "Y",
                }
            else:
                current["end"] = row.timestamp
                current["peak"] = max(current["peak"], float(temp))
                current["door_open"] = current["door_open"] or row.door_open == "Y"
            continue

        if is_missing:
            if current is not None:
                current["door_open"] = current["door_open"] or row.door_open == "Y"
            continue

        if current is not None:
            duration = int((current["end"] - current["start"]).total_seconds() / 60) + 1
            results.append(
                {
                    "shipment_id": current["shipment_id"],
                    "excursion_start": current["start"].strftime("%Y-%m-%d %H:%M"),
                    "excursion_end": current["end"].strftime("%Y-%m-%d %H:%M"),
                    "duration_minutes": duration,
                    "peak_temperature_c": current["peak"],
                    "door_open_during_excursion": "yes" if current["door_open"] else "no",
                }
            )
            current = None

    if current is not None:
        duration = int((current["end"] - current["start"]).total_seconds() / 60) + 1
        results.append(
            {
                "shipment_id": current["shipment_id"],
                "excursion_start": current["start"].strftime("%Y-%m-%d %H:%M"),
                "excursion_end": current["end"].strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": duration,
                "peak_temperature_c": current["peak"],
                "door_open_during_excursion": "yes" if current["door_open"] else "no",
            }
        )

output = pd.DataFrame(
    results,
    columns=[
        "shipment_id",
        "excursion_start",
        "excursion_end",
        "duration_minutes",
        "peak_temperature_c",
        "door_open_during_excursion",
    ],
).sort_values(["shipment_id", "excursion_start"]).reset_index(drop=True)

output.to_csv(output_dir / "shipment_excursion_audit.csv", index=False)
PY
