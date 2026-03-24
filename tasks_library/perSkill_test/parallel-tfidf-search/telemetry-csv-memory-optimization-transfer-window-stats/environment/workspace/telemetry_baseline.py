#!/usr/bin/env python3

from __future__ import annotations

import math
from collections import defaultdict

from telemetry_common import TelemetryWindowSummary, iter_telemetry_records, write_summary_json


def compute_window_statistics_baseline(csv_path, window_size=12, anomaly_sigma=2.25):
    rows = list(iter_telemetry_records(csv_path))
    grouped = defaultdict(list)
    for record in rows:
        grouped[record.sensor_id].append(record)

    summaries = []
    for sensor_id in sorted(grouped):
        records = grouped[sensor_id]
        complete_window_count = 0
        mean_total = 0.0
        peak_window_stddev = 0.0
        anomaly_count = 0
        strongest_anomaly_score = 0.0
        first_anomaly_timestamp = None

        for end_index in range(window_size - 1, len(records)):
            window_records = records[end_index + 1 - window_size : end_index + 1]
            readings = [record.reading for record in window_records]
            window_mean = sum(readings) / window_size
            variance = sum((reading - window_mean) * (reading - window_mean) for reading in readings) / window_size
            window_stddev = math.sqrt(variance)
            score = 0.0 if window_stddev == 0.0 else abs(readings[-1] - window_mean) / window_stddev

            complete_window_count += 1
            mean_total += window_mean
            if window_stddev > peak_window_stddev:
                peak_window_stddev = window_stddev
            if score > strongest_anomaly_score:
                strongest_anomaly_score = score
            if score >= anomaly_sigma:
                anomaly_count += 1
                if first_anomaly_timestamp is None:
                    first_anomaly_timestamp = window_records[-1].timestamp

        summaries.append(
            TelemetryWindowSummary(
                sensor_id=sensor_id,
                sample_count=len(records),
                complete_window_count=complete_window_count,
                mean_of_window_means=mean_total / complete_window_count if complete_window_count else 0.0,
                peak_window_stddev=peak_window_stddev,
                anomaly_count=anomaly_count,
                strongest_anomaly_score=strongest_anomaly_score,
                first_anomaly_timestamp=first_anomaly_timestamp,
            )
        )

    return summaries


def write_anomaly_summary_baseline_json(csv_path, output_path, window_size=12, anomaly_sigma=2.25):
    summaries = compute_window_statistics_baseline(
        csv_path,
        window_size=window_size,
        anomaly_sigma=anomaly_sigma,
    )
    write_summary_json(output_path, summaries)
