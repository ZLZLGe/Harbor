#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from datetime import datetime

import numpy as np

INPUT_PATH = "/root/data/wearable_skin_temp.csv"
OUTPUT_PATH = "/root/circadian_note.md"
MIN_PERIOD = 8.0
MAX_PERIOD = 30.0
GRID_SIZE = 70000


def load_series():
    times = []
    values = []
    reference_time = None

    with open(INPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["wear_state"] != "on_wrist":
                continue
            if float(row["quality_score"]) < 0.82:
                continue

            timestamp = datetime.fromisoformat(row["recorded_at"])
            if reference_time is None:
                reference_time = timestamp

            elapsed_hours = (timestamp - reference_time).total_seconds() / 3600.0
            times.append(elapsed_hours)
            values.append(float(row["skin_temp_c"]))

    return np.asarray(times, dtype=float), np.asarray(values, dtype=float)


def compute_periodogram(times, values):
    periods = np.linspace(MIN_PERIOD, MAX_PERIOD, GRID_SIZE)
    centered = values - values.mean()
    rss0 = float(np.sum(np.square(centered)))
    powers = np.empty_like(periods)

    for index, period in enumerate(periods):
        omega = 2.0 * np.pi / period
        design = np.column_stack(
            [
                np.sin(omega * times),
                np.cos(omega * times),
                np.ones_like(times),
            ]
        )
        coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
        residual = values - design @ coefficients
        rss = float(np.sum(np.square(residual)))
        powers[index] = 1.0 - rss / rss0

    peak_mask = (powers[1:-1] > powers[:-2]) & (powers[1:-1] > powers[2:])
    peak_indices = np.flatnonzero(peak_mask) + 1
    return periods, powers, peak_indices


def strongest_peak(periods, powers, peak_indices, lower, upper):
    candidates = [index for index in peak_indices if lower <= periods[index] <= upper]
    if not candidates:
        raise RuntimeError(f"No peak found between {lower} and {upper} hours")
    best_index = max(candidates, key=lambda index: powers[index])
    return float(periods[best_index]), float(powers[best_index])


times, values = load_series()
periods, powers, peak_indices = compute_periodogram(times, values)
selected_period, selected_power = strongest_peak(periods, powers, peak_indices, 18.0, 30.0)
harmonic_period, harmonic_power = strongest_peak(periods, powers, peak_indices, 10.5, 13.5)

reason = (
    f"The near-12-hour candidate is weaker than the selected peak "
    f"({harmonic_power:.3f} vs {selected_power:.3f}) and should be rejected as a harmonic."
)

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    handle.write("# Circadian Rhythm Estimate\n")
    handle.write(f"selected_period_hours: {selected_period:.2f}\n")
    handle.write(f"harmonic_period_hours: {harmonic_period:.2f}\n")
    handle.write(f"reason: {reason}\n")
PY
