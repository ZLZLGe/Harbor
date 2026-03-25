#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os

import numpy as np
import pandas as pd
from netCDF4 import Dataset

CONFIG_PATH = "/root/config/intake_profile.json"
NC_PATH = "/root/data/silverwood_reservoir_output.nc"
OUTPUT_PATH = "/root/reports/intake_alerts.json"


def isoformat(dt: pd.Timestamp) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    return {
        "reservoir_name": str(config["reservoir_name"]),
        "simulation_start": pd.Timestamp(config["simulation_start"]),
        "lake_depth_m": float(config["lake_depth_m"]),
        "intake_depth_m": float(config["intake_depth_m"]),
        "alert_threshold_c": float(config["alert_threshold_c"]),
    }


def extract_series(start: pd.Timestamp, lake_depth_m: float, intake_depth_m: float) -> pd.DataFrame:
    with Dataset(NC_PATH, "r") as ds:
        time_values = np.array(ds.variables["time"][:], dtype=float)
        z = ds.variables["z"][:]
        temp = ds.variables["temp"][:]

    rows = []
    for time_index, hour_offset in enumerate(time_values):
        timestamp = start + pd.Timedelta(hours=float(hour_offset))
        heights = z[time_index, :, 0, 0]
        temperatures = temp[time_index, :, 0, 0]

        best = None
        for height_value, temp_value in zip(heights, temperatures):
            if np.ma.is_masked(height_value) or np.ma.is_masked(temp_value):
                continue
            depth_from_surface = lake_depth_m - float(height_value)
            if depth_from_surface < 0 or depth_from_surface > lake_depth_m:
                continue
            candidate = (
                abs(depth_from_surface - intake_depth_m),
                -depth_from_surface,
                float(temp_value),
            )
            if best is None or candidate[:2] < best[:2]:
                best = candidate

        if best is None:
            continue

        rows.append(
            {
                "timestamp": timestamp,
                "temperature_c": best[2],
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def build_alerts(series: pd.DataFrame, threshold_c: float, time_step_hours: float):
    alerts = []
    current = None

    for row in series.itertuples(index=False):
        is_alert = row.temperature_c > threshold_c
        if is_alert:
            if current is None:
                current = {
                    "start_time": row.timestamp,
                    "end_time": row.timestamp,
                    "sample_count": 1,
                    "peak_temperature_c": float(row.temperature_c),
                }
            else:
                current["end_time"] = row.timestamp
                current["sample_count"] += 1
                current["peak_temperature_c"] = max(current["peak_temperature_c"], float(row.temperature_c))
        elif current is not None:
            current["duration_hours"] = current["sample_count"] * time_step_hours
            alerts.append(current)
            current = None

    if current is not None:
        current["duration_hours"] = current["sample_count"] * time_step_hours
        alerts.append(current)

    normalized = []
    for alert in alerts:
        normalized.append(
            {
                "start_time": isoformat(alert["start_time"]),
                "end_time": isoformat(alert["end_time"]),
                "sample_count": int(alert["sample_count"]),
                "duration_hours": float(alert["duration_hours"]),
                "peak_temperature_c": float(alert["peak_temperature_c"]),
            }
        )

    normalized.sort(key=lambda item: item["start_time"])
    return normalized


def choose_longest_alert(alerts):
    if not alerts:
        return None

    return max(
        alerts,
        key=lambda item: (
            item["duration_hours"],
            item["peak_temperature_c"],
            -pd.Timestamp(item["start_time"]).timestamp(),
        ),
    )


config = load_config()
series = extract_series(
    config["simulation_start"],
    config["lake_depth_m"],
    config["intake_depth_m"],
)

time_offsets = series["timestamp"].diff().dropna().dt.total_seconds().div(3600.0)
time_step_hours = float(time_offsets.iloc[0]) if not time_offsets.empty else 0.0
alerts = build_alerts(series, config["alert_threshold_c"], time_step_hours)
peak_temperature_c = float(series["temperature_c"].max()) if not series.empty else float("nan")

report = {
    "reservoir_name": config["reservoir_name"],
    "intake_depth_m": config["intake_depth_m"],
    "alert_threshold_c": config["alert_threshold_c"],
    "time_step_hours": time_step_hours,
    "evaluated_sample_count": int(len(series)),
    "peak_temperature_c": peak_temperature_c,
    "alerts": alerts,
    "longest_alert": choose_longest_alert(alerts),
}

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY
