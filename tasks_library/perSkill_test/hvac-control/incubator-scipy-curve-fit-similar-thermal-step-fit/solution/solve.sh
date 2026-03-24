#!/bin/bash
set -e

cd /root

python3 <<'PY'
import csv
import json

import numpy as np
from scipy.optimize import curve_fit


with open("incubator_run_info.json", "r") as f:
    run_info = json.load(f)

rows = []
with open("incubator_step_test.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(
            {
                "time_s": float(row["time_s"]),
                "phase": row["phase"],
                "heater_percent": float(row["heater_percent"]),
                "temperature_c": float(row["temperature_c"]),
            }
        )

ambient = float(run_info["ambient_temperature_c"])
target = float(run_info["target_temperature_c"])
heater_step = float(run_info["heater_step_percent"])
step_start = float(run_info["step_start_time_s"])

fit_rows = [row for row in rows if row["time_s"] >= step_start and row["heater_percent"] > 0.0]
t_data = np.array([row["time_s"] - step_start for row in fit_rows], dtype=float)
y_data = np.array([row["temperature_c"] for row in fit_rows], dtype=float)


def step_response(t, gain, tau):
    return ambient + gain * heater_step * (1.0 - np.exp(-t / tau))


gain_guess = max((float(np.mean(y_data[-5:])) - ambient) / heater_step, 0.05)
y63 = ambient + 0.632 * (float(np.mean(y_data[-5:])) - ambient)
tau_guess = float(t_data[np.argmin(np.abs(y_data - y63))])
tau_guess = max(tau_guess, float(run_info["sample_period_s"]))

popt, _ = curve_fit(
    step_response,
    t_data,
    y_data,
    p0=[gain_guess, tau_guess],
    bounds=([0.05, 30.0], [0.6, 4000.0]),
    maxfev=10000,
)

gain, tau = [float(value) for value in popt]
predicted = step_response(t_data, gain, tau)
residuals = y_data - predicted
rmse = float(np.sqrt(np.mean(residuals ** 2)))
ss_res = float(np.sum(residuals ** 2))
ss_tot = float(np.sum((y_data - np.mean(y_data)) ** 2))
r_squared = float(1.0 - ss_res / ss_tot)

report = {
    "experiment_id": run_info["experiment_id"],
    "input_file": "incubator_step_test.csv",
    "ambient_temperature_c": ambient,
    "target_temperature_c": target,
    "heater_step_percent": heater_step,
    "step_start_time_s": step_start,
    "samples_used": len(fit_rows),
    "model": {
        "gain_c_per_percent": gain,
        "time_constant_s": tau,
        "r_squared": r_squared,
        "rmse_c": rmse,
    },
    "predicted_equilibrium_at_step_c": float(ambient + gain * heater_step),
    "required_hold_heater_percent": float((target - ambient) / gain),
}

with open("incubator_fit_report.json", "w") as f:
    json.dump(report, f, indent=2)
PY
