#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import numpy as np


def moving_average(values, window):
    kernel = np.ones(window, dtype=float) / window
    pad = window // 2
    padded = np.pad(values, (pad, pad), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def load_light_curve(path):
    data = np.genfromtxt(path, delimiter=",", names=True)
    return (
        data["time_btjd"].astype(float),
        data["normalized_flux"].astype(float),
        data["quality_flag"].astype(int),
        data["flux_err"].astype(float),
    )


def load_ephemeris(path):
    with open(path, newline="") as f:
        row = next(csv.DictReader(f))
    period = float(row["period_days"])
    t0 = float(row["reference_mid_transit_btjd"])
    duration = float(row["transit_duration_hours"]) / 24.0
    return period, t0, duration


time, flux, quality, flux_err = load_light_curve("/root/data/known_transit_lc.csv")
period, t0, duration = load_ephemeris("/root/data/known_ephemeris.csv")

good = quality == 0
time = time[good]
flux = flux[good]
flux_err = flux_err[good]

# First-pass sigma clipping removes large outliers before detrending.
median_flux = np.median(flux)
mad_flux = np.median(np.abs(flux - median_flux))
sigma_flux = 1.4826 * mad_flux
keep = np.abs(flux - median_flux) <= 5.0 * sigma_flux
time = time[keep]
flux = flux[keep]
flux_err = flux_err[keep]

phase = ((time - t0 + 0.5 * period) % period) - 0.5 * period
transit_mask = np.abs(phase) <= 0.7 * duration

# Interpolate across transit cadences before smoothing so the trend estimate
# is not biased downward by the transits themselves.
interp_flux = np.interp(time, time[~transit_mask], flux[~transit_mask])
trend = moving_average(interp_flux, window=241)
flat_flux = flux / trend

# Second-pass clipping on the detrended series removes any residual spikes.
median_flat = np.median(flat_flux)
mad_flat = np.median(np.abs(flat_flux - median_flat))
sigma_flat = 1.4826 * mad_flat
keep = np.abs(flat_flux - median_flat) <= 5.0 * sigma_flat
time = time[keep]
flat_flux = flat_flux[keep]

in_transit_values = []
baseline_values = []

n_start = int(np.floor((time.min() - t0) / period)) - 1
n_stop = int(np.ceil((time.max() - t0) / period)) + 1
for n in range(n_start, n_stop + 1):
    mid_transit = t0 + n * period
    if mid_transit - 3.0 * duration < time.min():
        continue
    if mid_transit + 3.0 * duration > time.max():
        continue

    dt = time - mid_transit
    in_transit = np.abs(dt) <= duration / 2.0
    baseline = (np.abs(dt) >= duration) & (np.abs(dt) <= 3.0 * duration)
    if in_transit.sum() < 6 or baseline.sum() < 15:
        continue

    in_transit_values.extend(flat_flux[in_transit])
    baseline_values.extend(flat_flux[baseline])

depth = float(np.median(baseline_values) - np.median(in_transit_values))

with open("/root/transit_depth.txt", "w") as f:
    f.write(f"{depth:.6f}\n")
PY
