#!/bin/bash
set -euo pipefail

python3 <<'PY'
import numpy as np

INPUT_PATH = "/root/data/starspot_lightcurve.csv"
OUTPUT_PATH = "/root/rotation_period.txt"

data = np.genfromtxt(INPUT_PATH, delimiter=",", names=True)

time = data["time_day"]
flux = data["relative_flux"]
quality = data["quality_flag"]

good = quality == 0
time = time[good]
flux = flux[good]

median = np.median(flux)
mad = np.median(np.abs(flux - median))
robust_sigma = 1.4826 * mad if mad > 0 else np.std(flux)
keep = (flux > median - 6.0 * robust_sigma) & (flux < median + 5.0 * robust_sigma)

time = time[keep]
flux = flux[keep]
flux = flux - np.mean(flux)


def best_period(search_periods: np.ndarray) -> float:
    best_p = float(search_periods[0])
    best_power = -np.inf
    for period in search_periods:
        omega = 2.0 * np.pi / period
        design = np.column_stack(
            [
                np.sin(omega * time),
                np.cos(omega * time),
                np.ones_like(time),
            ]
        )
        coeffs, *_ = np.linalg.lstsq(design, flux, rcond=None)
        model = design @ coeffs
        power = float(np.var(model))
        if power > best_power:
            best_power = power
            best_p = float(period)
    return best_p


coarse_grid = np.linspace(2.0, 20.0, 8000)
coarse_period = best_period(coarse_grid)

fine_min = max(2.0, coarse_period - 0.6)
fine_max = min(20.0, coarse_period + 0.6)
fine_grid = np.linspace(fine_min, fine_max, 10000)
period = best_period(fine_grid)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(f"{period:.5f}\n")
PY
