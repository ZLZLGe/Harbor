#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
cd "$ROOT_DIR"

python3 <<'PY'
import csv
import json
import math
import os
from pathlib import Path

import numpy as np


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
PROFILE_PATH = ROOT / "chamber_profile.json"
LOG_PATH = ROOT / "heating_step_log.csv"
OUTPUT_PATH = ROOT / "fermentation_model_fit.json"


def load_profile():
    with PROFILE_PATH.open() as f:
        return json.load(f)


def load_rows():
    with LOG_PATH.open(newline="") as f:
        return [
            {
                "elapsed_min": float(row["elapsed_min"]),
                "heater_power_pct": float(row["heater_power_pct"]),
                "temperature_c": float(row["temperature_c"]),
            }
            for row in csv.DictReader(f)
        ]


def fit_step_response(times, temps, ambient, heater_power):
    observed_delta = max(temps[-1] - ambient, 0.5)
    k_guess = observed_delta / heater_power
    k_min = max(0.01, 0.5 * k_guess)
    k_max = max(k_min + 0.02, 1.5 * k_guess)
    tau_min = 1.0
    tau_max = max(8.0, 3.0 * times[-1])

    def evaluate(k, tau):
        predicted = ambient + k * heater_power * (1.0 - np.exp(-times / tau))
        return float(np.sqrt(np.mean((temps - predicted) ** 2)))

    best_rmse = None
    best_k = None
    best_tau = None

    for k in np.linspace(k_min, k_max, 240):
        for tau in np.linspace(tau_min, tau_max, 240):
            rmse = evaluate(k, tau)
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_k = float(k)
                best_tau = float(tau)

    refine_k_min = max(0.01, best_k * 0.85)
    refine_k_max = best_k * 1.15
    refine_tau_min = max(0.5, best_tau * 0.75)
    refine_tau_max = best_tau * 1.25

    for k in np.linspace(refine_k_min, refine_k_max, 320):
        for tau in np.linspace(refine_tau_min, refine_tau_max, 320):
            rmse = evaluate(k, tau)
            if rmse < best_rmse:
                best_rmse = rmse
                best_k = float(k)
                best_tau = float(tau)

    predicted = ambient + best_k * heater_power * (1.0 - np.exp(-times / best_tau))
    residuals = temps - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((temps - np.mean(temps)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return best_k, best_tau, r_squared, float(np.sqrt(np.mean(residuals ** 2)))


def minutes_to_target(ambient, gain_k, heater_power, tau_min, target_c):
    steady_state = ambient + gain_k * heater_power
    if target_c >= steady_state:
        raise ValueError("target temperature is not reachable with the fitted model")
    fraction = 1.0 - (target_c - ambient) / (gain_k * heater_power)
    return float(-tau_min * math.log(fraction))


profile = load_profile()
rows = load_rows()

idle_rows = [row for row in rows if row["heater_power_pct"] == 0.0]
step_rows = [row for row in rows if row["heater_power_pct"] > 0.0]

ambient = float(np.mean([row["temperature_c"] for row in idle_rows]))
step_start = step_rows[0]["elapsed_min"]
times = np.array([row["elapsed_min"] - step_start for row in step_rows], dtype=float)
temps = np.array([row["temperature_c"] for row in step_rows], dtype=float)
heater_power = float(profile["heater_power_percent"])

gain_k, tau_min, r_squared, rmse_c = fit_step_response(times, temps, ambient, heater_power)

target_min, target_max = [float(v) for v in profile["target_band_c"]]
target_mid = (target_min + target_max) / 2.0

result = {
    "batch_id": profile["batch_id"],
    "log_file": profile["step_log_file"],
    "ambient_temperature_c": round(ambient, 6),
    "heater_power_percent": heater_power,
    "fitted_model": {
        "K": round(gain_k, 6),
        "tau_min": round(tau_min, 6),
        "r_squared": round(r_squared, 6),
        "rmse_c": round(rmse_c, 6),
    },
    "predictions": {
        "target_band_c": [target_min, target_max],
        "minutes_from_step_to_target_min": round(minutes_to_target(ambient, gain_k, heater_power, tau_min, target_min), 6),
        "minutes_from_step_to_target_midpoint": round(minutes_to_target(ambient, gain_k, heater_power, tau_min, target_mid), 6),
        "minutes_from_step_to_target_max": round(minutes_to_target(ambient, gain_k, heater_power, tau_min, target_max), 6),
    },
}

with OUTPUT_PATH.open("w") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
