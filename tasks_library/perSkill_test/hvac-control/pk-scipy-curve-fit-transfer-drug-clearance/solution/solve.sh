#!/bin/bash
set -e

cd /root

python3 <<'PY'
import json
import math

import numpy as np
from scipy.optimize import curve_fit


with open("iv_bolus_case.json", "r") as f:
    case = json.load(f)

samples = case["samples"]
times = np.array([row["time_hr"] for row in samples], dtype=float)
concentrations = np.array(
    [row["plasma_concentration_mg_per_l"] for row in samples],
    dtype=float,
)


def decay_model(t, c0, elimination_rate):
    return c0 * np.exp(-elimination_rate * t)


log_slope, log_intercept = np.polyfit(times, np.log(concentrations), 1)
c0_guess = float(math.exp(log_intercept))
elimination_guess = float(max(-log_slope, 0.05))

popt, _ = curve_fit(
    decay_model,
    times,
    concentrations,
    p0=[c0_guess, elimination_guess],
    bounds=([1.0, 0.01], [100.0, 5.0]),
    maxfev=10000,
)

c0, elimination_rate = [float(value) for value in popt]
predicted = decay_model(times, c0, elimination_rate)
rmse = float(np.sqrt(np.mean((concentrations - predicted) ** 2)))
half_life = float(math.log(2.0) / elimination_rate)
auc_0_inf = float(c0 / elimination_rate)

volume = float(case["volume_of_distribution_l"])
clearance = float(elimination_rate * volume)
discharge_time = float(case["discharge_time_hr"])
floor = float(case["subtherapeutic_floor_mg_per_l"])
predicted_at_discharge = float(decay_model(discharge_time, c0, elimination_rate))
time_to_floor = float(math.log(c0 / floor) / elimination_rate)

summary = {
    "case_id": case["case_id"],
    "drug_name": case["drug_name"],
    "input_file": "iv_bolus_case.json",
    "dose_mg": float(case["dose_mg"]),
    "samples_used": len(samples),
    "fit_model": {
        "initial_concentration_mg_per_l": c0,
        "elimination_rate_per_hr": elimination_rate,
        "half_life_hr": half_life,
        "auc_0_inf_mg_h_per_l": auc_0_inf,
        "rmse_mg_per_l": rmse,
    },
    "discharge_summary": {
        "volume_of_distribution_l": volume,
        "clearance_l_per_hr": clearance,
        "discharge_time_hr": discharge_time,
        "subtherapeutic_floor_mg_per_l": floor,
        "predicted_concentration_at_discharge_mg_per_l": predicted_at_discharge,
        "time_to_fall_below_floor_hr": time_to_floor,
        "dose_due_before_discharge": bool(time_to_floor <= discharge_time),
    },
}

with open("pk_decay_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
PY
