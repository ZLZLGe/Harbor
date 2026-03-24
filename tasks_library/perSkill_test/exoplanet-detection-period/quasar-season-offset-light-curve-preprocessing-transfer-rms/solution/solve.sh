#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path


def running_median(values, window):
    half_window = window // 2
    medians = []
    for idx in range(len(values)):
        lo = max(0, idx - half_window)
        hi = min(len(values), idx + half_window + 1)
        medians.append(statistics.median(values[lo:hi]))
    return medians


def get_input_path():
    candidates = [
        Path("/root/data/quasar_monitoring.csv"),
        Path("environment/data/quasar_monitoring.csv"),
        Path("data/quasar_monitoring.csv"),
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except PermissionError:
            continue
    raise FileNotFoundError("quasar_monitoring.csv not found")


def get_output_path():
    requested = Path(os.environ.get("OUTPUT_PATH", "/root/quasar_rms.txt"))
    if requested.parent.exists() and os.access(requested.parent, os.W_OK):
        return requested
    return Path("quasar_rms.txt")


rows = []
with get_input_path().open(newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if int(row["quality_flag"]) != 0:
            continue
        rows.append(
            {
                "mjd": float(row["mjd"]),
                "relative_flux": float(row["relative_flux"]),
                "season_id": int(row["season_id"]),
            }
        )

rows.sort(key=lambda row: (row["season_id"], row["mjd"]))
by_season = defaultdict(list)
for row in rows:
    by_season[row["season_id"]].append(row)

all_residuals = []
for season_id in sorted(by_season):
    season_rows = by_season[season_id]
    flux = [row["relative_flux"] for row in season_rows]
    baseline = running_median(flux, 5)
    residual = [value - trend for value, trend in zip(flux, baseline)]
    center = statistics.median(residual)
    sigma = 1.4826 * statistics.median(abs(value - center) for value in residual)

    cleaned_rows = [
        row
        for row, value in zip(season_rows, residual)
        if abs(value - center) <= 4.5 * sigma
    ]

    cleaned_flux = [row["relative_flux"] for row in cleaned_rows]
    season_median = statistics.median(cleaned_flux)
    normalized_flux = [value / season_median for value in cleaned_flux]
    seasonal_trend = running_median(normalized_flux, 9)
    season_residuals = [value / trend - 1.0 for value, trend in zip(normalized_flux, seasonal_trend)]
    all_residuals.extend(season_residuals)

rms = math.sqrt(sum(value * value for value in all_residuals) / len(all_residuals))
output_path = get_output_path()
output_path.write_text(f"{rms:.6f}\n")
PY
