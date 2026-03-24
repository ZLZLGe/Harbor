#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
export ROOT_DIR

cd "$ROOT_DIR"

python3 <<'PY'
import json
import os

import numpy as np

from reservoir_simulator import ReservoirSimulator


OUTPUT_PATH = os.path.join(os.environ["ROOT_DIR"], "tank_level_response_fit.json")


def run_step_test(sim, baseline_duration_sec, valve_step_percent, total_duration_sec):
    dt = sim.get_dt()
    initial_level = sim.reset()

    samples = [{
        "time_s": 0.0,
        "level_cm": round(initial_level, 4),
        "valve_open_percent": 0.0,
    }]

    baseline_steps = int(round(baseline_duration_sec / dt))
    total_steps = int(round(total_duration_sec / dt))

    for _ in range(baseline_steps):
        result = sim.step(0.0)
        samples.append({
            "time_s": result["time_s"],
            "level_cm": result["level_cm"],
            "valve_open_percent": result["valve_open_percent"],
        })

    for _ in range(total_steps - baseline_steps):
        result = sim.step(valve_step_percent)
        samples.append({
            "time_s": result["time_s"],
            "level_cm": result["level_cm"],
            "valve_open_percent": result["valve_open_percent"],
        })

    return samples


def fit_first_order(samples, step_start_time_sec, valve_step_percent):
    baseline_rows = [row for row in samples if row["time_s"] <= step_start_time_sec]
    step_rows = [row for row in samples if row["time_s"] > step_start_time_sec]

    baseline_level = float(np.mean([row["level_cm"] for row in baseline_rows]))
    t0 = step_rows[0]["time_s"]
    t_data = np.array([row["time_s"] - t0 for row in step_rows], dtype=float)
    y_data = np.array([row["level_cm"] for row in step_rows], dtype=float)
    centered_output = y_data - baseline_level

    tau_candidates = np.linspace(80.0, 320.0, 481)
    best_rmse = float("inf")
    best_gain = None
    best_tau = None

    for tau_candidate in tau_candidates:
        basis = 1.0 - np.exp(-t_data / tau_candidate)
        amplitude = float(np.dot(basis, centered_output) / np.dot(basis, basis))
        gain_candidate = max(0.01, amplitude / valve_step_percent)
        predictions = baseline_level + valve_step_percent * gain_candidate * basis
        rmse = float(np.sqrt(np.mean((y_data - predictions) ** 2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_gain = gain_candidate
            best_tau = float(tau_candidate)

    predicted_final_level_cm = baseline_level + valve_step_percent * best_gain
    return float(best_gain), float(best_tau), float(best_rmse), float(predicted_final_level_cm)


def main():
    np.random.seed(23)
    sim = ReservoirSimulator(os.path.join(os.environ["ROOT_DIR"], "reservoir_profile.json"))

    baseline_duration_sec = 24.0
    valve_step_percent = 36.0
    total_duration_sec = 584.0
    samples = run_step_test(sim, baseline_duration_sec, valve_step_percent, total_duration_sec)

    steady_gain_cm_per_percent, time_constant_sec, fit_rmse_cm, predicted_final_level_cm = fit_first_order(
        samples,
        baseline_duration_sec,
        valve_step_percent,
    )

    report = {
        "excitation_plan": {
            "baseline_duration_sec": baseline_duration_sec,
            "valve_step_percent": valve_step_percent,
            "sample_interval_sec": sim.get_dt(),
            "total_duration_sec": total_duration_sec,
            "overflow_limit_cm": sim.get_overflow_level(),
        },
        "level_response": samples,
        "identified_model": {
            "steady_gain_cm_per_percent": steady_gain_cm_per_percent,
            "time_constant_sec": time_constant_sec,
            "fit_rmse_cm": fit_rmse_cm,
            "predicted_final_level_cm": predicted_final_level_cm,
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
