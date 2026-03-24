#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/bedside_vitals.csv ]; then
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


def build_alerts(group: pd.DataFrame, alert_type: str, value_column: str, comparator, extreme_kind: str):
    rows = []
    current = None

    for row in group.itertuples(index=False):
        value = getattr(row, value_column)
        if pd.isna(value):
            continue

        timestamp = row.timestamp
        is_alert = comparator(float(value))

        if is_alert:
            if current is None:
                current = {
                    "start": timestamp,
                    "end": timestamp,
                    "extreme": float(value),
                }
            else:
                current["end"] = timestamp
                if extreme_kind == "max":
                    current["extreme"] = max(current["extreme"], float(value))
                else:
                    current["extreme"] = min(current["extreme"], float(value))
            continue

        if current is not None:
            rows.append(
                {
                    "patient_id": row.patient_id,
                    "alert_type": alert_type,
                    "alert_start": current["start"].strftime("%Y-%m-%d %H:%M"),
                    "alert_end": current["end"].strftime("%Y-%m-%d %H:%M"),
                    "extreme_value": current["extreme"],
                    "recovery_time_minutes": int((timestamp - current["end"]).total_seconds() / 60),
                }
            )
            current = None

    if current is not None:
        rows.append(
            {
                "patient_id": group.iloc[0]["patient_id"],
                "alert_type": alert_type,
                "alert_start": current["start"].strftime("%Y-%m-%d %H:%M"),
                "alert_end": current["end"].strftime("%Y-%m-%d %H:%M"),
                "extreme_value": current["extreme"],
                "recovery_time_minutes": None,
            }
        )

    return rows


input_dir = Path(os.environ["INPUT_DIR"])
output_dir = Path(os.environ["OUTPUT_DIR"])

df = pd.read_csv(input_dir / "bedside_vitals.csv", na_values=[""])
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["patient_id", "timestamp"]).reset_index(drop=True)

results = []
for _, group in df.groupby("patient_id", sort=False):
    results.extend(
        build_alerts(
            group,
            "high_heart_rate",
            "heart_rate_bpm",
            lambda value: value > 120,
            "max",
        )
    )
    results.extend(
        build_alerts(
            group,
            "low_spo2",
            "spo2_percent",
            lambda value: value < 90,
            "min",
        )
    )

output = pd.DataFrame(
    results,
    columns=[
        "patient_id",
        "alert_type",
        "alert_start",
        "alert_end",
        "extreme_value",
        "recovery_time_minutes",
    ],
).sort_values(["patient_id", "alert_start", "alert_type"]).reset_index(drop=True)

output.to_csv(output_dir / "patient_alert_windows.csv", index=False)
PY
