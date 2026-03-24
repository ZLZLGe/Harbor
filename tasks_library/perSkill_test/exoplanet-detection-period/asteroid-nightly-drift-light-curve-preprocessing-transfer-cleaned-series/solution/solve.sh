#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import numpy as np


def running_median(values, window):
    half_window = window // 2
    med = np.empty_like(values)
    for idx in range(len(values)):
        lo = max(0, idx - half_window)
        hi = min(len(values), idx + half_window + 1)
        med[idx] = np.median(values[lo:hi])
    return med


data = np.genfromtxt(
    "/root/data/asteroid_ground_photometry.csv",
    delimiter=",",
    names=True,
    dtype=None,
    encoding="utf-8",
)

time = data["time_jd"].astype(float)
flux = data["diff_flux"].astype(float)
night_id = data["night_id"].astype(int)
quality_flag = data["quality_flag"].astype(int)

keep = quality_flag == 0
time = time[keep]
flux = flux[keep]
night_id = night_id[keep]

all_times = []
all_fluxes = []

for night in np.unique(night_id):
    night_mask = night_id == night
    night_time = time[night_mask]
    night_flux = flux[night_mask]

    local_median = running_median(night_flux, 21)
    residual = night_flux - local_median
    residual_center = np.median(residual)
    sigma = 1.4826 * np.median(np.abs(residual - residual_center))
    keep_night = np.abs(residual - residual_center) <= 5.0 * sigma

    night_time = night_time[keep_night]
    night_flux = night_flux[keep_night]

    night_flux = night_flux / np.median(night_flux)
    x = night_time - np.median(night_time)
    design = np.column_stack([np.ones_like(x), x])
    coeffs, _, _, _ = np.linalg.lstsq(design, night_flux, rcond=None)
    trend = design @ coeffs
    clean_flux = night_flux / trend

    all_times.append(night_time)
    all_fluxes.append(clean_flux)

clean_time = np.concatenate(all_times)
clean_flux = np.concatenate(all_fluxes)
order = np.argsort(clean_time)
clean_time = clean_time[order]
clean_flux = clean_flux[order]
clean_flux = clean_flux / np.median(clean_flux)

with open("/root/asteroid_cleaned.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["time_jd", "clean_flux"])
    for t, fval in zip(clean_time, clean_flux):
        writer.writerow([f"{t:.10f}", f"{fval:.6f}"])
PY
