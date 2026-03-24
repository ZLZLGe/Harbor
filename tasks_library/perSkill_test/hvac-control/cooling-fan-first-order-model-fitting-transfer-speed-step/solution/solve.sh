#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
cd "$TASK_ROOT"

python3 <<'PY'
import csv
import json
import math
import os
import tomllib

import numpy as np


TASK_ROOT = os.environ.get("TASK_ROOT", "/root")
PROFILE_PATH = f"{TASK_ROOT}/fan_step_profile.toml"
TRACE_PATH = f"{TASK_ROOT}/fan_speed_trace.csv"
OUTPUT_PATH = f"{TASK_ROOT}/fan_speed_fit.json"


def load_profile():
    with open(PROFILE_PATH, "rb") as f:
        return tomllib.load(f)


def load_rows():
    with open(TRACE_PATH, newline="") as f:
        return [
            {
                "timestamp_s": float(row["timestamp_s"]),
                "pwm_percent": float(row["pwm_percent"]),
                "fan_speed_rpm": float(row["fan_speed_rpm"]),
            }
            for row in csv.DictReader(f)
        ]


def fit_model(times, speeds, baseline, step_amplitude):
    observed_delta = max(float(speeds[-1] - baseline), 100.0)
    gain_guess = observed_delta / step_amplitude
    gain_min = max(1.0, 0.7 * gain_guess)
    gain_max = max(gain_min + 2.0, 1.3 * gain_guess)
    tau_min = 0.5
    tau_max = max(8.0, 0.8 * float(times[-1]))

    best_rmse = None
    best_gain = None
    best_tau = None

    for gain in np.linspace(gain_min, gain_max, 260):
        for tau in np.linspace(tau_min, tau_max, 280):
            predicted = baseline + gain * step_amplitude * (1.0 - np.exp(-times / tau))
            rmse = float(np.sqrt(np.mean((speeds - predicted) ** 2)))
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    for gain in np.linspace(max(0.5, best_gain * 0.9), best_gain * 1.1, 320):
        for tau in np.linspace(max(0.2, best_tau * 0.8), best_tau * 1.2, 320):
            predicted = baseline + gain * step_amplitude * (1.0 - np.exp(-times / tau))
            rmse = float(np.sqrt(np.mean((speeds - predicted) ** 2)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    predicted = baseline + best_gain * step_amplitude * (1.0 - np.exp(-times / best_tau))
    residuals = speeds - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((speeds - np.mean(speeds)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "gain_rpm_per_pwm_pct": best_gain,
        "tau_s": best_tau,
        "steady_state_speed_rpm": baseline + best_gain * step_amplitude,
        "r_squared": r_squared,
        "rmse_rpm": float(np.sqrt(np.mean(residuals ** 2))),
    }


def main():
    profile = load_profile()
    rows = load_rows()
    step_time = float(profile["step_time_s"])
    step_amplitude = float(profile["pwm_after_percent"] - profile["pwm_before_percent"])

    pre_rows = [row for row in rows if row["timestamp_s"] < step_time]
    post_rows = [row for row in rows if row["timestamp_s"] >= step_time]

    baseline = float(np.mean([row["fan_speed_rpm"] for row in pre_rows]))
    times = np.array([row["timestamp_s"] - step_time for row in post_rows], dtype=float)
    speeds = np.array([row["fan_speed_rpm"] for row in post_rows], dtype=float)

    fitted = fit_model(times, speeds, baseline, step_amplitude)
    steady_state = fitted["steady_state_speed_rpm"]

    time_to_targets = {}
    target_speeds = {}
    for percent in profile["target_percentages_of_speed_rise"]:
        fraction = float(percent) / 100.0
        key = f"p{int(percent)}"
        time_to_targets[key] = float(-fitted["tau_s"] * math.log(1.0 - fraction))
        target_speeds[key] = float(baseline + fraction * (steady_state - baseline))

    output = {
        "run_id": profile["run_id"],
        "samples_file": profile["samples_file"],
        "baseline_speed_rpm": baseline,
        "pwm_step_percent": step_amplitude,
        "fitted_model": fitted,
        "response_predictions": {
            "target_percentages_of_speed_rise": [float(v) for v in profile["target_percentages_of_speed_rise"]],
            "time_to_targets_s": time_to_targets,
            "predicted_target_speeds_rpm": target_speeds,
        },
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")


main()
PY
