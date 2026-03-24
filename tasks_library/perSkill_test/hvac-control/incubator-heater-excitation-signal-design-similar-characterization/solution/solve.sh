#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
export ROOT_DIR

cd "$ROOT_DIR"

python3 <<'PY'
import json
import os

import numpy as np

from incubator_simulator import IncubatorSimulator


REPORT_PATH = os.path.join(os.environ["ROOT_DIR"], "incubator_identification_report.json")


def run_step_test(sim, baseline_duration_sec, heater_step_percent, test_duration_sec):
    dt = sim.get_dt()
    sim.reset()
    samples = []

    baseline_steps = int(round(baseline_duration_sec / dt))
    total_steps = int(round(test_duration_sec / dt))

    for _ in range(baseline_steps):
        result = sim.step(0.0)
        samples.append(result)

    for _ in range(total_steps - baseline_steps):
        result = sim.step(heater_step_percent)
        samples.append(result)

    return samples


def fit_first_order(samples, step_start_time_sec, heater_step_percent):
    baseline_samples = [row["temperature_c"] for row in samples if row["time_s"] <= step_start_time_sec]
    step_samples = [row for row in samples if row["time_s"] > step_start_time_sec]

    baseline_temp = float(np.mean(baseline_samples))
    t0 = step_samples[0]["time_s"]
    t_data = np.array([row["time_s"] - t0 for row in step_samples], dtype=float)
    y_data = np.array([row["temperature_c"] for row in step_samples], dtype=float)

    centered_output = y_data - baseline_temp
    tau_candidates = np.linspace(30.0, 240.0, 421)
    best_rmse = float("inf")
    best_gain = None
    best_tau = None
    best_predictions = None

    for tau_candidate in tau_candidates:
        basis = 1.0 - np.exp(-t_data / tau_candidate)
        amplitude = float(np.dot(basis, centered_output) / np.dot(basis, basis))
        gain_candidate = max(0.01, amplitude / heater_step_percent)
        predictions = baseline_temp + heater_step_percent * gain_candidate * basis
        rmse = float(np.sqrt(np.mean((y_data - predictions) ** 2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_gain = gain_candidate
            best_tau = float(tau_candidate)
            best_predictions = predictions

    gain_c_per_percent = float(best_gain)
    time_constant_sec = float(best_tau)
    predictions = best_predictions
    fit_rmse_c = float(np.sqrt(np.mean((y_data - predictions) ** 2)))
    return float(gain_c_per_percent), float(time_constant_sec), fit_rmse_c


def main():
    np.random.seed(7)
    sim = IncubatorSimulator(os.path.join(os.environ["ROOT_DIR"], "incubator_profile.json"))

    baseline_duration_sec = 20.0
    heater_step_percent = 30.0
    test_duration_sec = 420.0
    samples = run_step_test(sim, baseline_duration_sec, heater_step_percent, test_duration_sec)

    gain_c_per_percent, time_constant_sec, fit_rmse_c = fit_first_order(
        samples,
        baseline_duration_sec,
        heater_step_percent,
    )

    report = {
        "heater_step_percent": heater_step_percent,
        "sample_interval_sec": sim.get_dt(),
        "step_start_time_sec": baseline_duration_sec,
        "test_duration_sec": test_duration_sec,
        "safety_limit_c": sim.get_safety_limit(),
        "raw_response": samples,
        "identified_model": {
            "gain_c_per_percent": gain_c_per_percent,
            "time_constant_sec": time_constant_sec,
            "fit_rmse_c": fit_rmse_c,
        },
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
