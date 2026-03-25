#!/bin/bash
set -euo pipefail

mkdir -p /root/output

python3 <<'PY'
import json
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.time import Time, TimeDelta
from astropy.timeseries import BoxLeastSquares

DATA_PATH = Path("/root/data/api_success_rates.jsonl")
OUTPUT_PATH = Path("/root/output/maintenance_window_forecast.md")

timestamps = []
success_rate = []

for line in DATA_PATH.read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    timestamps.append(row["timestamp_utc"].replace("Z", ""))
    success_rate.append(float(row["success_rate"]))

times = Time(timestamps, format="isot", scale="utc")
base_time = times[0]
relative_time = (times - base_time).to_value(u.day) * u.day
success_rate = np.asarray(success_rate, dtype=float)

duration_grid = np.linspace(20.0, 80.0, 31) * u.min
model = BoxLeastSquares(relative_time, success_rate)
periodogram = model.autopower(
    duration_grid,
    minimum_period=12 * u.hour,
    maximum_period=30 * u.hour,
    objective="snr",
)

best_idx = int(np.argmax(periodogram.power))
best_period = periodogram.period[best_idx]
best_duration = periodogram.duration[best_idx]
best_center = base_time + TimeDelta(periodogram.transit_time[best_idx].to_value(u.day), format="jd")

period_delta = TimeDelta(best_period.to_value(u.day), format="jd")
half_duration = TimeDelta(best_duration.to_value(u.day) / 2.0, format="jd")

first_window_start = best_center - half_duration
while first_window_start - period_delta >= base_time:
    first_window_start -= period_delta
while first_window_start < base_time:
    first_window_start += period_delta

next_window_start = first_window_start + period_delta


def format_utc(value: Time) -> str:
    return value.utc.isot.split(".")[0] + "Z"


lines = [
    "# API Maintenance Window Forecast",
    f"- recurrence_hours: {best_period.to_value(u.hour):.5f}",
    f"- window_minutes: {best_duration.to_value(u.min):.5f}",
    f"- first_window_start_utc: {format_utc(first_window_start)}",
    f"- next_window_start_utc: {format_utc(next_window_start)}",
]

OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
