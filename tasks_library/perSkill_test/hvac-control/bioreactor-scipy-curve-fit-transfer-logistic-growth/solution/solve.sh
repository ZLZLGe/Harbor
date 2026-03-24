#!/bin/bash
set -e

cd /root

python3 <<'PY'
import json
import math

import numpy as np
from scipy.optimize import curve_fit


INPUT_PATH = "/root/bioreactor_batch_run.json"
OUTPUT_PATH = "/root/bioreactor_growth_fit.json"


def logistic_model(time_hr, carrying_capacity, growth_rate, midpoint_time):
    return carrying_capacity / (1.0 + np.exp(-growth_rate * (time_hr - midpoint_time)))


def inverse_logistic(target_od, carrying_capacity, growth_rate, midpoint_time):
    return midpoint_time - math.log(carrying_capacity / target_od - 1.0) / growth_rate


with open(INPUT_PATH, "r") as f:
    batch = json.load(f)

observations = batch["observations"]
times = np.array([row["time_hr"] for row in observations], dtype=float)
ods = np.array([row["od600"] for row in observations], dtype=float)

initial_guess = [
    float(max(ods) * 1.02),
    0.3,
    float(np.median(times)),
]
bounds = (
    [float(max(ods) * 0.95), 0.01, float(min(times))],
    [3.0, 2.0, float(max(times))],
)

popt, _ = curve_fit(
    logistic_model,
    times,
    ods,
    p0=initial_guess,
    bounds=bounds,
    maxfev=20000,
)

carrying_capacity, growth_rate, midpoint_time = [float(value) for value in popt]
predicted = logistic_model(times, *popt)
residuals = ods - predicted
rmse = float(np.sqrt(np.mean(residuals ** 2)))
ss_res = float(np.sum(residuals ** 2))
ss_tot = float(np.sum((ods - np.mean(ods)) ** 2))
r_squared = float(1.0 - ss_res / ss_tot)

initial_od = float(logistic_model(np.array([0.0]), *popt)[0])
lag_adjusted_onset = float(midpoint_time - 2.0 / growth_rate)
max_growth_rate = float(carrying_capacity * growth_rate / 4.0)

target_harvest = float(batch["target_harvest_od600"])
latest_recommended = float(batch["latest_recommended_od600"])
time_to_target = float(
    inverse_logistic(target_harvest, carrying_capacity, growth_rate, midpoint_time)
)
time_to_latest = float(
    inverse_logistic(latest_recommended, carrying_capacity, growth_rate, midpoint_time)
)

report = {
    "batch_id": batch["batch_id"],
    "input_file": "bioreactor_batch_run.json",
    "reactor_volume_l": float(batch["reactor_volume_l"]),
    "target_harvest_od600": target_harvest,
    "latest_recommended_od600": latest_recommended,
    "samples_used": len(observations),
    "fit_model": {
        "initial_od600": initial_od,
        "carrying_capacity_od600": carrying_capacity,
        "growth_rate_per_hr": growth_rate,
        "midpoint_time_hr": midpoint_time,
        "lag_adjusted_onset_hr": lag_adjusted_onset,
        "max_growth_rate_od600_per_hr": max_growth_rate,
        "rmse_od600": rmse,
        "r_squared": r_squared,
    },
    "harvest_forecast": {
        "time_to_target_od600_hr": time_to_target,
        "time_to_latest_recommended_od600_hr": time_to_latest,
        "harvest_window_start_hr": time_to_target,
        "harvest_window_end_hr": time_to_latest,
        "predicted_window_width_hr": float(time_to_latest - time_to_target),
    },
}

with open(OUTPUT_PATH, "w") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY
