#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import numpy as np

INPUT_PATH = "/root/data/rv_visits.csv"
OUTPUT_PATH = "/root/rv_period_report.json"
MIN_PERIOD = 0.6
MAX_PERIOD = 8.0
MIN_SEPARATION = 0.2

data = np.genfromtxt(INPUT_PATH, delimiter=",", names=True, dtype=None, encoding="utf-8")

keep = data["status"] == "keep"
time = data["bjd_day"][keep]
velocity = data["rv_mps"][keep] - data["template_drift_mps"][keep]
error = data["rv_err_mps"][keep]
weights = 1.0 / np.square(error)

periods = np.linspace(MIN_PERIOD, MAX_PERIOD, 60000)
baseline = np.sum(weights * np.square(velocity - np.average(velocity, weights=weights)))
power = np.empty_like(periods)

sqrt_weights = np.sqrt(weights)
for index, period in enumerate(periods):
    omega = 2.0 * np.pi / period
    design = np.column_stack(
        [
            np.sin(omega * time),
            np.cos(omega * time),
            np.ones_like(time),
        ]
    )
    coefficients, *_ = np.linalg.lstsq(design * sqrt_weights[:, None], velocity * sqrt_weights, rcond=None)
    model = design @ coefficients
    residual = velocity - model
    chi_squared = np.sum(weights * np.square(residual))
    power[index] = 1.0 - chi_squared / baseline

peak_mask = (power[1:-1] > power[:-2]) & (power[1:-1] > power[2:])
peak_indices = np.flatnonzero(peak_mask) + 1

ranked_periods = []
for peak_index in sorted(peak_indices, key=lambda idx: power[idx], reverse=True):
    candidate = float(periods[peak_index])
    if all(abs(candidate - existing) >= MIN_SEPARATION for existing in ranked_periods):
        ranked_periods.append(candidate)
    if len(ranked_periods) == 3:
        break

report = {
    "primary_period_days": round(ranked_periods[0], 5),
    "alternate_periods_days": [round(ranked_periods[1], 5), round(ranked_periods[2], 5)],
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY
