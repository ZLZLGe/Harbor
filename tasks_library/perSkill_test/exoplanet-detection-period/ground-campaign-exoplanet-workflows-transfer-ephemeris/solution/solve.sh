#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np


def detrend_night(path: Path):
    data = np.genfromtxt(path, delimiter=",", names=True)
    good = data["quality_flag"] == 0
    time = data["time_bjd_tdb"][good]
    flux = data["relative_flux"][good]
    flux_err = data["flux_err"][good]
    airmass = data["airmass"][good]

    x = time - np.mean(time)
    design = np.column_stack(
        [
            np.ones_like(x),
            x,
            x * x,
            airmass - np.median(airmass),
        ]
    )

    keep = np.ones_like(flux, dtype=bool)
    for _ in range(4):
        coeff = np.linalg.lstsq(design[keep], flux[keep], rcond=None)[0]
        trend = design @ coeff
        residual = flux - trend
        sigma = 1.4826 * np.median(np.abs(residual[keep] - np.median(residual[keep]))) + 1e-6
        keep = residual > -2.2 * sigma

    flattened = flux / trend * np.median(trend)
    baseline = np.median(flattened[keep])
    transit_mask = flattened < baseline - 0.004

    midpoint = None
    if np.count_nonzero(transit_mask) >= 5:
        weights = np.clip(baseline - flattened[transit_mask], 1e-5, None)
        midpoint = float(np.average(time[transit_mask], weights=weights))

    return {
        "time": time,
        "flux": flattened,
        "flux_err": flux_err,
        "midpoint": midpoint,
    }


night_dir = Path("/root/data/nights")
midpoints = []
for csv_path in sorted(night_dir.glob("night_*.csv")):
    result = detrend_night(csv_path)
    if result["midpoint"] is not None:
        midpoints.append(result["midpoint"])

midpoints = np.array(sorted(midpoints))
if midpoints.size < 4:
    raise RuntimeError("Not enough transit nights were recovered to fit an ephemeris")

pair_differences = []
for i in range(midpoints.size):
    for j in range(i + 1, midpoints.size):
        pair_differences.append(midpoints[j] - midpoints[i])
pair_differences = np.array(pair_differences)

best_score = None
best_period = None
for period in np.linspace(3.5, 5.0, 15001):
    residuals = []
    for diff in pair_differences:
        cycles = max(1, round(diff / period))
        residuals.append(abs(diff / cycles - period))
    score = float(np.mean(residuals))
    if best_score is None or score < best_score:
        best_score = score
        best_period = float(period)

epochs = np.array([round((midpoint - midpoints[0]) / best_period) for midpoint in midpoints])
design = np.column_stack([np.ones_like(epochs), epochs])
reference_mid_transit, refined_period = np.linalg.lstsq(design, midpoints, rcond=None)[0]

output = {
    "period_days": round(float(refined_period), 5),
    "reference_mid_transit_bjd_tdb": round(float(reference_mid_transit), 5),
    "observed_mid_transits_bjd_tdb": [round(float(value), 5) for value in midpoints],
    "time_system": "BJD_TDB",
}

Path("/root/ephemeris.json").write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
PY
