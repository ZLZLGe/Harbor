#!/bin/bash

python3 <<'PY'
import math
from pathlib import Path

import pandas as pd

script = """import math
import pandas as pd


INPUT_FILE = 'drive_telemetry.csv'
OUTPUT_FILE = 'following_window_summary.csv'
CRITICAL_GAP_THRESHOLD_M = 15.0
OUTPUT_COLUMNS = [
    'window_id',
    'window_type',
    'start_time_s',
    'end_time_s',
    'sample_count',
    'avg_ego_speed_mps',
    'min_gap_m',
    'valid_ttc_count',
    'avg_valid_ttc_s',
    'min_valid_ttc_s',
]


def classify_window(row):
    if pd.isna(row['lead_speed_mps']) or pd.isna(row['gap_m']):
        return 'open_road'
    if row['gap_m'] <= CRITICAL_GAP_THRESHOLD_M:
        return 'critical_gap'
    return 'following'


def compute_ttc(row):
    if pd.isna(row['lead_speed_mps']) or pd.isna(row['gap_m']):
        return math.nan
    relative_speed = row['ego_speed_mps'] - row['lead_speed_mps']
    if relative_speed <= 0:
        return math.nan
    return row['gap_m'] / relative_speed


def rounded_or_none(value):
    if pd.isna(value):
        return None
    return round(float(value), 3)


df = pd.read_csv(INPUT_FILE, na_values=['', 'NA', 'null'])
df['window_type'] = df.apply(classify_window, axis=1)
df['ttc_s'] = df.apply(compute_ttc, axis=1)

window_ids = []
current_id = -1
previous_type = None
for window_type in df['window_type']:
    if window_type != previous_type:
        current_id += 1
        previous_type = window_type
    window_ids.append(current_id)
df['window_id'] = window_ids

rows = []
for window_id, group in df.groupby('window_id', sort=True):
    window_type = group['window_type'].iloc[0]
    valid_ttc = group['ttc_s'].dropna()
    min_gap = group['gap_m'].min() if group['gap_m'].notna().any() else None

    rows.append({
        'window_id': int(window_id),
        'window_type': window_type,
        'start_time_s': rounded_or_none(group['time_s'].min()),
        'end_time_s': rounded_or_none(group['time_s'].max()),
        'sample_count': int(len(group)),
        'avg_ego_speed_mps': rounded_or_none(group['ego_speed_mps'].mean()),
        'min_gap_m': rounded_or_none(min_gap),
        'valid_ttc_count': int(valid_ttc.shape[0]),
        'avg_valid_ttc_s': rounded_or_none(valid_ttc.mean()) if not valid_ttc.empty else None,
        'min_valid_ttc_s': rounded_or_none(valid_ttc.min()) if not valid_ttc.empty else None,
    })

summary_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
summary_df.to_csv(OUTPUT_FILE, index=False)
"""

Path("/root/summarize_following_windows.py").write_text(script)

df = pd.read_csv("/root/drive_telemetry.csv", na_values=["", "NA", "null"])

def classify_window(row):
    if pd.isna(row["lead_speed_mps"]) or pd.isna(row["gap_m"]):
        return "open_road"
    if row["gap_m"] <= 15.0:
        return "critical_gap"
    return "following"


def compute_ttc(row):
    if pd.isna(row["lead_speed_mps"]) or pd.isna(row["gap_m"]):
        return math.nan
    relative_speed = row["ego_speed_mps"] - row["lead_speed_mps"]
    if relative_speed <= 0:
        return math.nan
    return row["gap_m"] / relative_speed


def rounded_or_none(value):
    if pd.isna(value):
        return None
    return round(float(value), 3)


df["window_type"] = df.apply(classify_window, axis=1)
df["ttc_s"] = df.apply(compute_ttc, axis=1)

window_ids = []
current_id = -1
previous_type = None
for window_type in df["window_type"]:
    if window_type != previous_type:
        current_id += 1
        previous_type = window_type
    window_ids.append(current_id)
df["window_id"] = window_ids

rows = []
for window_id, group in df.groupby("window_id", sort=True):
    valid_ttc = group["ttc_s"].dropna()
    min_gap = group["gap_m"].min() if group["gap_m"].notna().any() else None
    rows.append(
        {
            "window_id": int(window_id),
            "window_type": group["window_type"].iloc[0],
            "start_time_s": rounded_or_none(group["time_s"].min()),
            "end_time_s": rounded_or_none(group["time_s"].max()),
            "sample_count": int(len(group)),
            "avg_ego_speed_mps": rounded_or_none(group["ego_speed_mps"].mean()),
            "min_gap_m": rounded_or_none(min_gap),
            "valid_ttc_count": int(valid_ttc.shape[0]),
            "avg_valid_ttc_s": rounded_or_none(valid_ttc.mean()) if not valid_ttc.empty else None,
            "min_valid_ttc_s": rounded_or_none(valid_ttc.min()) if not valid_ttc.empty else None,
        }
    )

summary_df = pd.DataFrame(
    rows,
    columns=[
        "window_id",
        "window_type",
        "start_time_s",
        "end_time_s",
        "sample_count",
        "avg_ego_speed_mps",
        "min_gap_m",
        "valid_ttc_count",
        "avg_valid_ttc_s",
        "min_valid_ttc_s",
    ],
)
summary_df.to_csv("/root/following_window_summary.csv", index=False)
PY
