#!/bin/bash
set -euo pipefail

python3 <<'PY'
import numpy as np
import astropy.units as u
from astropy.timeseries import BoxLeastSquares

data = np.genfromtxt(
    "/root/data/eclipsing_binary_survey.csv",
    delimiter=",",
    names=True,
    dtype=float,
)

time = np.asarray(data["time_bjd"], dtype=float)
flux = np.asarray(data["relative_flux"], dtype=float)
flux_err = np.asarray(data["flux_err"], dtype=float)

mask = np.isfinite(time) & np.isfinite(flux) & np.isfinite(flux_err) & (flux_err > 0)
time = time[mask]
flux = flux[mask]
flux_err = flux_err[mask]

median = np.median(flux)
mad = np.median(np.abs(flux - median))
scatter = 1.4826 * mad if mad > 0 else np.std(flux)
if scatter > 0:
    keep = np.abs(flux - median) < 6.0 * scatter
    time = time[keep]
    flux = flux[keep]
    flux_err = flux_err[keep]

flux = flux / np.median(flux)

model = BoxLeastSquares(time * u.day, flux, dy=flux_err)
durations = np.linspace(0.08, 0.24, 17) * u.day


def best_peak(period_min, period_max, n_periods):
    periods = np.linspace(period_min, period_max, n_periods) * u.day
    result = model.power(periods, durations, objective="snr")
    idx = int(np.argmax(result.power))
    return (
        result.period[idx].to_value(u.day),
        float(result.power[idx]),
    )


coarse_period, coarse_power = best_peak(1.2, 5.5, 6000)
fine_min = max(1.2, coarse_period - 0.15)
fine_max = min(5.5, coarse_period + 0.15)
best_period, best_power = best_peak(fine_min, fine_max, 8000)

# Check the common eclipsing-binary half-period alias.
if best_period * 2.0 <= 5.5:
    doubled_period, doubled_power = best_peak(best_period * 2.0 - 0.05, best_period * 2.0 + 0.05, 4000)
    if doubled_power > best_power * 0.92:
        best_period = doubled_period

with open("/root/binary_period.txt", "w", encoding="utf-8") as fh:
    fh.write(f"{best_period:.5f}\n")
PY
