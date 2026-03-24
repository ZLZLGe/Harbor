#!/bin/bash
set -euo pipefail

python3 <<'PY'
import numpy as np
import astropy.units as u
from astropy.timeseries import BoxLeastSquares

data = np.genfromtxt(
    "/root/data/cheops_gapped_lc.csv",
    delimiter=",",
    names=True,
    dtype=float,
)

time = np.asarray(data["time_bjd"], dtype=float)
flux = np.asarray(data["normalized_flux"], dtype=float)
flux_err = np.asarray(data["flux_err"], dtype=float)

mask = np.isfinite(time) & np.isfinite(flux) & np.isfinite(flux_err) & (flux_err > 0)
time = time[mask]
flux = flux[mask]
flux_err = flux_err[mask]

median = np.median(flux)
mad = np.median(np.abs(flux - median))
scatter = 1.4826 * mad if mad > 0 else np.std(flux)
if scatter > 0:
    keep = np.abs(flux - median) < 5.0 * scatter
    time = time[keep]
    flux = flux[keep]
    flux_err = flux_err[keep]

flux = flux / np.median(flux)

model = BoxLeastSquares(time * u.day, flux, dy=flux_err)
durations = np.linspace(0.08, 0.18, 11)


def run_search(period_min, period_max, n_periods):
    periods = np.linspace(period_min, period_max, n_periods) * u.day
    best_score = -np.inf
    best_period = None
    for duration in durations:
        result = model.power(periods, duration * u.day, objective="snr")
        idx = int(np.argmax(result.power))
        score = float(result.power[idx])
        if score > best_score:
            best_score = score
            best_period = result.period[idx].to_value(u.day)
    return best_period


coarse_period = run_search(1.5, 8.0, 3500)
best_period = run_search(max(1.5, coarse_period - 0.2), min(8.0, coarse_period + 0.2), 5000)

with open("/root/planet_period.txt", "w", encoding="utf-8") as fh:
    fh.write(f"{best_period:.5f}\n")
PY
