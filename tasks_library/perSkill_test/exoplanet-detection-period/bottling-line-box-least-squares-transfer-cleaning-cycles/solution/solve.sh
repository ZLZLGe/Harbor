#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

import numpy as np
import pandas as pd
import astropy.units as u
from astropy.timeseries import BoxLeastSquares


DATA_PATH = Path("/root/data/bottling_lines.csv")
OUTPUT_PATH = Path("/root/output/cleaning_shutdown_report.csv")
MIN_PERIOD = 140 * u.min
MAX_PERIOD = 260 * u.min
DURATIONS = np.linspace(12, 36, 25) * u.min


def analyze_line(frame: pd.DataFrame) -> dict:
    time = frame["minute_index"].to_numpy() * u.min
    flux = frame["normalized_throughput"].to_numpy()

    model = BoxLeastSquares(time, flux)
    periodogram = model.autopower(
        DURATIONS,
        minimum_period=MIN_PERIOD,
        maximum_period=MAX_PERIOD,
        objective="snr",
    )

    best_idx = int(np.argmax(periodogram.power))
    period_minutes = periodogram.period[best_idx].to_value(u.min)
    duration_minutes = periodogram.duration[best_idx].to_value(u.min)

    return {
        "line_id": str(frame["line_id"].iloc[0]),
        "shutdown_period_minutes": period_minutes,
        "shutdown_duration_minutes": duration_minutes,
        "downtime_fraction": duration_minutes / period_minutes,
        "peak_power": float(periodogram.power[best_idx]),
    }


df = pd.read_csv(DATA_PATH)
candidates = [analyze_line(part.reset_index(drop=True)) for _, part in df.groupby("line_id", sort=False)]
best = max(candidates, key=lambda item: item["peak_power"])

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "line_id",
            "shutdown_period_minutes",
            "shutdown_duration_minutes",
            "downtime_fraction",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "line_id": best["line_id"],
            "shutdown_period_minutes": f'{best["shutdown_period_minutes"]:.5f}',
            "shutdown_duration_minutes": f'{best["shutdown_duration_minutes"]:.5f}',
            "downtime_fraction": f'{best["downtime_fraction"]:.5f}',
        }
    )
PY
