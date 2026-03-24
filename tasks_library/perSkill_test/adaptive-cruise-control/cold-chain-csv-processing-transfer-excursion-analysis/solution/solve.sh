#!/bin/bash
set -euo pipefail

cat > /root/analyze_excursions.py <<'PY'
import json
from datetime import timedelta

import pandas as pd


TEMP_PATH = "/root/temperature_log.csv"
DOOR_PATH = "/root/door_events.csv"
OUTPUT_PATH = "/root/excursion_windows.csv"
SUMMARY_PATH = "/root/excursion_summary.json"
SAMPLE_MINUTES = 10


def build_door_intervals(events: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    intervals = []
    open_time = None
    for row in events.sort_values("event_time").itertuples(index=False):
        if row.event_type == "open":
            open_time = row.event_time
        elif row.event_type == "close" and open_time is not None:
            if row.event_time > open_time:
                intervals.append((open_time, row.event_time))
            open_time = None
    return intervals


temps = pd.read_csv(TEMP_PATH)
temps["recorded_at"] = pd.to_datetime(temps["recorded_at"])
temps = temps.sort_values(["compartment", "recorded_at"]).reset_index(drop=True)
temps["filled_temperature_c"] = temps.groupby("compartment")["temperature_c"].ffill()
temps["was_imputed"] = temps["temperature_c"].isna() & temps["filled_temperature_c"].notna()
temps["is_excursion"] = temps["filled_temperature_c"] > temps["upper_limit_c"]

door_events = pd.read_csv(DOOR_PATH)
door_events["event_time"] = pd.to_datetime(door_events["event_time"])
door_intervals = build_door_intervals(door_events)

windows = []
for compartment, group in temps.groupby("compartment", sort=True):
    active_rows = []
    for row in group.itertuples(index=False):
        if row.is_excursion:
            active_rows.append(row)
            continue
        if not active_rows:
            continue
        samples = pd.DataFrame(active_rows)
        windows.append((compartment, samples))
        active_rows = []
    if active_rows:
        samples = pd.DataFrame(active_rows)
        windows.append((compartment, samples))

records = []
for compartment, samples in windows:
    start_time = samples["recorded_at"].iloc[0]
    end_time = samples["recorded_at"].iloc[-1] + timedelta(minutes=SAMPLE_MINUTES)
    peak_temp = float(samples["filled_temperature_c"].max())
    peak_rows = samples[samples["filled_temperature_c"] == peak_temp]
    peak_time = peak_rows["recorded_at"].iloc[0]
    limit_c = float(samples["upper_limit_c"].iloc[0])

    door_open_minutes = 0
    door_open_cycle_count = 0
    for open_time, close_time in door_intervals:
        overlap_start = max(start_time, open_time)
        overlap_end = min(end_time, close_time)
        if overlap_start < overlap_end:
            door_open_minutes += int((overlap_end - overlap_start).total_seconds() // 60)
            door_open_cycle_count += 1

    records.append(
        {
            "compartment": compartment,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
            "sample_count": int(len(samples)),
            "imputed_sample_count": int(samples["was_imputed"].sum()),
            "duration_minutes": int((end_time - start_time).total_seconds() // 60),
            "limit_c": round(limit_c, 3),
            "max_temperature_c": round(peak_temp, 3),
            "max_excursion_c": round(peak_temp - limit_c, 3),
            "peak_recorded_at": peak_time.strftime("%Y-%m-%dT%H:%M"),
            "door_open_minutes": int(door_open_minutes),
            "door_open_during_window": "true" if door_open_minutes > 0 else "false",
            "door_open_cycle_count": int(door_open_cycle_count),
        }
    )

output = pd.DataFrame(records).sort_values(["compartment", "start_time"]).reset_index(drop=True)
output.insert(0, "window_id", [f"EXC-{index:03d}" for index in range(1, len(output) + 1)])
output = output[
    [
        "window_id",
        "compartment",
        "start_time",
        "end_time",
        "sample_count",
        "imputed_sample_count",
        "duration_minutes",
        "limit_c",
        "max_temperature_c",
        "max_excursion_c",
        "peak_recorded_at",
        "door_open_minutes",
        "door_open_during_window",
        "door_open_cycle_count",
    ]
]
output.to_csv(OUTPUT_PATH, index=False)

summary = {
    "window_count": int(len(output)),
    "affected_compartments": sorted(output["compartment"].unique().tolist()),
    "windows_with_door_open": int((output["door_open_minutes"] > 0).sum()),
    "longest_window_minutes": int(output["duration_minutes"].max()),
    "worst_excursion_c": round(float(output["max_excursion_c"].max()), 3),
    "total_door_open_minutes_during_excursions": int(output["door_open_minutes"].sum()),
}

with open(SUMMARY_PATH, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
PY

python3 /root/analyze_excursions.py
