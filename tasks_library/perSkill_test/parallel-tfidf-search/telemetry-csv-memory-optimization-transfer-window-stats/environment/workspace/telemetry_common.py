#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    timestamp: str
    sensor_id: str
    reading: float


@dataclass(frozen=True, slots=True)
class TelemetryWindowSummary:
    sensor_id: str
    sample_count: int
    complete_window_count: int
    mean_of_window_means: float
    peak_window_stddev: float
    anomaly_count: int
    strongest_anomaly_score: float
    first_anomaly_timestamp: str | None


def iter_telemetry_records(csv_path):
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield TelemetryRecord(
                timestamp=row["timestamp"],
                sensor_id=row["sensor_id"],
                reading=float(row["reading"]),
            )


def summary_to_dict(summary: TelemetryWindowSummary) -> dict[str, object]:
    payload = asdict(summary)
    payload["mean_of_window_means"] = round(summary.mean_of_window_means, 6)
    payload["peak_window_stddev"] = round(summary.peak_window_stddev, 6)
    payload["strongest_anomaly_score"] = round(summary.strongest_anomaly_score, 6)
    return payload


def write_summary_json(output_path, summaries) -> None:
    serialized = [summary_to_dict(summary) for summary in summaries]
    Path(output_path).write_text(json.dumps(serialized, indent=2), encoding="utf-8")
