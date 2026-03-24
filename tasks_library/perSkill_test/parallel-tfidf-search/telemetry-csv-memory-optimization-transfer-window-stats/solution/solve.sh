#!/bin/bash
set -euo pipefail

cat <<'PYTHON_EOF' > /root/workspace/telemetry_window_solution.py
#!/usr/bin/env python3

from __future__ import annotations

import math
import sys
from collections import deque
from dataclasses import dataclass, field

from telemetry_common import TelemetryWindowSummary, iter_telemetry_records, write_summary_json


@dataclass(slots=True)
class _SensorState:
    readings: deque = field(default_factory=deque)
    reading_sum: float = 0.0
    reading_sq_sum: float = 0.0
    sample_count: int = 0
    complete_window_count: int = 0
    total_window_mean: float = 0.0
    peak_window_stddev: float = 0.0
    anomaly_count: int = 0
    strongest_anomaly_score: float = 0.0
    first_anomaly_timestamp: str | None = None


def compute_window_statistics(csv_path, window_size=12, anomaly_sigma=2.25):
    states = {}

    for record in iter_telemetry_records(csv_path):
        sensor_id = sys.intern(record.sensor_id)
        state = states.get(sensor_id)
        if state is None:
            state = _SensorState()
            states[sensor_id] = state

        readings = state.readings
        if len(readings) == window_size:
            removed = readings.popleft()
            state.reading_sum -= removed
            state.reading_sq_sum -= removed * removed

        reading = record.reading
        readings.append(reading)
        state.reading_sum += reading
        state.reading_sq_sum += reading * reading
        state.sample_count += 1

        if len(readings) < window_size:
            continue

        window_mean = state.reading_sum / window_size
        variance = (state.reading_sq_sum / window_size) - (window_mean * window_mean)
        if variance < 0.0 and variance > -1e-12:
            variance = 0.0
        elif variance < 0.0:
            variance = 0.0
        window_stddev = math.sqrt(variance)
        score = 0.0 if window_stddev == 0.0 else abs(reading - window_mean) / window_stddev

        state.complete_window_count += 1
        state.total_window_mean += window_mean
        if window_stddev > state.peak_window_stddev:
            state.peak_window_stddev = window_stddev
        if score > state.strongest_anomaly_score:
            state.strongest_anomaly_score = score
        if score >= anomaly_sigma:
            state.anomaly_count += 1
            if state.first_anomaly_timestamp is None:
                state.first_anomaly_timestamp = record.timestamp

    summaries = []
    for sensor_id in sorted(states):
        state = states[sensor_id]
        summaries.append(
            TelemetryWindowSummary(
                sensor_id=sensor_id,
                sample_count=state.sample_count,
                complete_window_count=state.complete_window_count,
                mean_of_window_means=(
                    state.total_window_mean / state.complete_window_count
                    if state.complete_window_count
                    else 0.0
                ),
                peak_window_stddev=state.peak_window_stddev,
                anomaly_count=state.anomaly_count,
                strongest_anomaly_score=state.strongest_anomaly_score,
                first_anomaly_timestamp=state.first_anomaly_timestamp,
            )
        )

    return summaries


def write_anomaly_summary_json(csv_path, output_path, window_size=12, anomaly_sigma=2.25):
    summaries = compute_window_statistics(
        csv_path,
        window_size=window_size,
        anomaly_sigma=anomaly_sigma,
    )
    write_summary_json(output_path, summaries)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("output_path")
    parser.add_argument("--window-size", type=int, default=12)
    parser.add_argument("--anomaly-sigma", type=float, default=2.25)
    args = parser.parse_args()

    write_anomaly_summary_json(
        args.csv_path,
        args.output_path,
        window_size=args.window_size,
        anomaly_sigma=args.anomaly_sigma,
    )
PYTHON_EOF

chmod +x /root/workspace/telemetry_window_solution.py
