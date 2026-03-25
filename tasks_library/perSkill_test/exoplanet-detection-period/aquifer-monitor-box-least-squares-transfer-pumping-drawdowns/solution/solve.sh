#!/bin/bash
set -euo pipefail

mkdir -p /root/output

python3 <<'PY'
import csv
from pathlib import Path
from statistics import median
from datetime import datetime

import astropy.units as u
import numpy as np
from astropy.timeseries import BoxLeastSquares


DATA_PATH = Path("/root/data/well_drawdowns.tsv")
OUTPUT_PATH = Path("/root/output/pumping_drawdown_report.txt")
MIN_PERIOD = 10 * u.hour
MAX_PERIOD = 30 * u.hour
DURATIONS = np.linspace(45, 180, 19) * u.min


def parse_rows():
    grouped = {}
    with DATA_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            grouped.setdefault(row["well_id"], []).append(
                (
                    datetime.strptime(row["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ"),
                    float(row["head_anomaly_m"]),
                )
            )
    return grouped


def split_segments(mask):
    segments = []
    start = None
    for idx, flag in enumerate(mask):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            segments.append((start, idx))
            start = None
    if start is not None:
        segments.append((start, len(mask)))
    return segments


def analyze_well(points):
    start_time = points[0][0]
    elapsed_hours = np.array(
        [(timestamp - start_time).total_seconds() / 3600.0 for timestamp, _ in points],
        dtype=float,
    )
    values = np.array([value for _, value in points], dtype=float)

    model = BoxLeastSquares(elapsed_hours * u.hour, values)
    periodogram = model.autopower(
        DURATIONS,
        minimum_period=MIN_PERIOD,
        maximum_period=MAX_PERIOD,
        objective="snr",
    )

    best_idx = int(np.argmax(periodogram.power))
    period_hours = periodogram.period[best_idx].to_value(u.hour)
    duration_hours = periodogram.duration[best_idx].to_value(u.hour)
    reference_hours = periodogram.transit_time[best_idx].to_value(u.hour)
    peak_power = float(np.asarray(periodogram.power[best_idx]).reshape(-1)[0])

    phase = ((elapsed_hours - reference_hours + 0.5 * period_hours) % period_hours) - 0.5 * period_hours
    mask = np.abs(phase) <= (0.5 * duration_hours + 1e-12)
    segments = split_segments(mask)
    depths = [abs(float(np.min(values[start:end]))) for start, end in segments]

    return {
        "period_hours": period_hours,
        "median_drawdown_meters": float(median(depths)),
        "event_count": len(segments),
        "peak_power": peak_power,
    }


grouped = parse_rows()
results = {well_id: analyze_well(points) for well_id, points in grouped.items()}
best_well_id, best = max(results.items(), key=lambda item: item[1]["peak_power"])

OUTPUT_PATH.write_text(
    "\n".join(
        [
            "Aquifer Pumping Drawdown Report",
            f"well_id: {best_well_id}",
            f"drawdown_period_hours: {best['period_hours']:.5f}",
            f"median_drawdown_meters: {best['median_drawdown_meters']:.5f}",
            f"event_count: {best['event_count']}",
        ]
    )
    + "\n",
    encoding="utf-8",
)
PY
