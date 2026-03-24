#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import math
from pathlib import Path

import numpy as np


LIGHTCURVE_PATH = Path("/root/data/alias_validation_lc.txt")
CANDIDATE_PATH = Path("/root/data/candidate_periods.csv")
OUTPUT_PATH = Path("/root/validated_period.txt")
TRANSIT_DURATION_DAYS = 0.245


def running_mean(values, window):
    kernel = np.ones(window, dtype=float) / window
    smooth = np.convolve(values, kernel, mode="same")
    edge = window // 2
    if edge > 0:
        smooth[:edge] = np.median(values[:window])
        smooth[-edge:] = np.median(values[-window:])
    return smooth


data = np.loadtxt(LIGHTCURVE_PATH, skiprows=1)
time = data[:, 0]
flux = data[:, 1]
quality = data[:, 2].astype(int)
flux_err = data[:, 3]

usable = quality == 0
time = time[usable]
flux = flux[usable]
flux_err = flux_err[usable]

median_flux = np.median(flux)
mad = np.median(np.abs(flux - median_flux))
robust_sigma = 1.4826 * mad if mad > 0 else np.std(flux)
keep = np.abs(flux - median_flux) < 5.0 * robust_sigma
time = time[keep]
flux = flux[keep]
flux_err = flux_err[keep]

cadence = np.median(np.diff(time))
window = max(21, int(round(1.5 / cadence)))
if window % 2 == 0:
    window += 1

trend = running_mean(flux, window)
flat_flux = flux / trend


def candidate_score(period, t0):
    first_epoch = math.floor((time.min() - t0) / period) - 1
    last_epoch = math.ceil((time.max() - t0) / period) + 1

    event_depths = []
    for epoch in range(first_epoch, last_epoch + 1):
        center = t0 + epoch * period
        offsets = time - center

        in_transit = np.abs(offsets) < TRANSIT_DURATION_DAYS / 2.0
        local_baseline = (np.abs(offsets) > TRANSIT_DURATION_DAYS) & (
            np.abs(offsets) < 3.0 * TRANSIT_DURATION_DAYS
        )

        if np.count_nonzero(in_transit) < 3 or np.count_nonzero(local_baseline) < 6:
            continue

        baseline_level = np.median(flat_flux[local_baseline])
        transit_level = np.median(flat_flux[in_transit])
        event_depths.append(baseline_level - transit_level)

    event_depths = np.asarray(event_depths)
    if event_depths.size < 3:
        return -np.inf

    median_depth = float(np.median(event_depths))
    scatter = float(np.std(event_depths))

    # Reward candidates that produce repeated, similarly deep events.
    return median_depth / (scatter + 1.0e-4) + 0.4 * event_depths.size


best_period = None
best_score = -np.inf

with CANDIDATE_PATH.open(newline="") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        period = float(row["period_days"])
        t0 = float(row["reference_epoch_bjd_minus_2457000"])
        score = candidate_score(period, t0)
        if score > best_score:
            best_score = score
            best_period = period

if best_period is None:
    raise RuntimeError("No valid period candidate could be scored")

OUTPUT_PATH.write_text(f"{best_period:.5f}\n", encoding="ascii")
print(f"Validated period: {best_period:.5f} d")
PY
