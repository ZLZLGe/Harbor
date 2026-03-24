#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import os
from collections import deque
from datetime import datetime


DATA_DIR = os.environ.get("DATA_DIR", "/root/data")
INPUT_CSV = os.path.join(DATA_DIR, "accelerometer_records.csv")
STATIONS_CSV = os.path.join(DATA_DIR, "stations.csv")
OUTPUT_CSV = os.environ.get("OUTPUT_CSV", "/root/alert_windows.csv")


def read_csv_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def rolling_mean(values, window):
    queue = deque()
    running_sum = 0.0
    means = []
    for value in values:
        queue.append(value)
        running_sum += value
        if len(queue) > window:
            running_sum -= queue.popleft()
        means.append(running_sum / len(queue))
    return means


wave_rows = read_csv_rows(INPUT_CSV)
station_rows = read_csv_rows(STATIONS_CSV)
times = [datetime.fromisoformat(row["time"]) for row in wave_rows]

if len(times) < 2:
    raise ValueError("accelerometer_records.csv must contain at least two samples")

dt = (times[1] - times[0]).total_seconds()
short_window = max(3, round(0.30 / dt))
long_window = max(short_window + 1, round(2.50 / dt))
baseline_samples = max(1, round(3.0 / dt))
search_start = round(2.5 / dt)

results = []
for station in station_rows:
    trace_column = station["trace_column"]
    abs_values = [abs(float(row[trace_column])) for row in wave_rows]
    baseline = abs_values[:baseline_samples]
    baseline_mean = sum(baseline) / len(baseline)
    baseline_var = sum((value - baseline_mean) ** 2 for value in baseline) / len(baseline)
    baseline_std = baseline_var ** 0.5

    sta = rolling_mean(abs_values, short_window)
    lta = rolling_mean(abs_values, long_window)
    amplitude_threshold = baseline_mean + 5.5 * baseline_std

    candidate_index = None
    for idx in range(search_start, len(abs_values) - 2):
        trigger_score = sta[idx] / max(lta[idx], baseline_mean + 1e-6)
        is_trigger = sta[idx] >= amplitude_threshold and trigger_score >= 2.6
        next_trigger = sta[idx + 1] >= amplitude_threshold and sta[idx + 1] / max(lta[idx + 1], baseline_mean + 1e-6) >= 2.6
        third_trigger = sta[idx + 2] >= amplitude_threshold and sta[idx + 2] / max(lta[idx + 2], baseline_mean + 1e-6) >= 2.6
        if is_trigger and next_trigger and third_trigger:
            candidate_index = idx
            break

    if candidate_index is None:
        raise RuntimeError(f"Could not find an alert window for station {station['station']}")

    trigger_score = sta[candidate_index] / max(lta[candidate_index], baseline_mean + 1e-6)
    look_ahead = max(1, round(1.0 / dt))
    peak_accel = max(abs_values[candidate_index : candidate_index + look_ahead])
    results.append(
        {
            "station": station["station"],
            "window_start": times[candidate_index].isoformat(timespec="milliseconds"),
            "trigger_score": f"{trigger_score:.3f}",
            "peak_accel": f"{peak_accel:.3f}",
        }
    )

results.sort(key=lambda row: row["window_start"])

with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["station", "window_start", "trigger_score", "peak_accel"])
    writer.writeheader()
    writer.writerows(results)
PY
