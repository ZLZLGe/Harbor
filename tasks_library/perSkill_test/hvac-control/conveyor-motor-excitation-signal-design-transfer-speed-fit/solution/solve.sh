#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
export ROOT_DIR

cd "$ROOT_DIR"

python3 <<'PY'
import json
import os

import numpy as np

from motor_bench import ConveyorMotorBench


OUTPUT_PATH = os.path.join(os.environ["ROOT_DIR"], "motor_speed_model.json")


def run_step_test(bench, baseline_duration_sec, pwm_step_percent, total_duration_sec):
    dt = bench.get_dt()
    initial_speed = bench.reset()

    samples = [{
        "time_s": 0.0,
        "speed_rpm": round(initial_speed, 4),
        "pwm_percent": 0.0,
    }]

    baseline_steps = int(round(baseline_duration_sec / dt))
    total_steps = int(round(total_duration_sec / dt))

    for _ in range(baseline_steps):
        result = bench.step(0.0)
        samples.append({
            "time_s": result["time_s"],
            "speed_rpm": result["speed_rpm"],
            "pwm_percent": result["pwm_percent"],
        })

    for _ in range(total_steps - baseline_steps):
        result = bench.step(pwm_step_percent)
        samples.append({
            "time_s": result["time_s"],
            "speed_rpm": result["speed_rpm"],
            "pwm_percent": result["pwm_percent"],
        })

    return samples


def fit_first_order(samples, step_start_time_sec, pwm_step_percent):
    baseline_rows = [row for row in samples if row["time_s"] <= step_start_time_sec]
    step_rows = [row for row in samples if row["time_s"] > step_start_time_sec]

    baseline_speed = float(np.mean([row["speed_rpm"] for row in baseline_rows]))
    t0 = step_rows[0]["time_s"]
    t_data = np.array([row["time_s"] - t0 for row in step_rows], dtype=float)
    y_data = np.array([row["speed_rpm"] for row in step_rows], dtype=float)
    centered_output = y_data - baseline_speed

    tau_candidates = np.linspace(0.15, 1.2, 421)
    best_rmse = float("inf")
    best_gain = None
    best_tau = None

    for tau_candidate in tau_candidates:
        basis = 1.0 - np.exp(-t_data / tau_candidate)
        amplitude = float(np.dot(basis, centered_output) / np.dot(basis, basis))
        gain_candidate = max(0.1, amplitude / pwm_step_percent)
        predictions = baseline_speed + pwm_step_percent * gain_candidate * basis
        rmse = float(np.sqrt(np.mean((y_data - predictions) ** 2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_gain = gain_candidate
            best_tau = float(tau_candidate)

    return float(best_gain), float(best_tau), float(best_rmse)


def main():
    np.random.seed(11)
    bench = ConveyorMotorBench(os.path.join(os.environ["ROOT_DIR"], "motor_bench_config.json"))

    baseline_duration_sec = 0.3
    pwm_step_percent = 36.0
    total_duration_sec = 2.7
    samples = run_step_test(bench, baseline_duration_sec, pwm_step_percent, total_duration_sec)

    steady_gain_rpm_per_percent, time_constant_sec, fit_rmse_rpm = fit_first_order(
        samples,
        baseline_duration_sec,
        pwm_step_percent,
    )

    report = {
        "excitation_plan": {
            "baseline_duration_sec": baseline_duration_sec,
            "pwm_step_percent": pwm_step_percent,
            "sample_interval_sec": bench.get_dt(),
            "total_duration_sec": total_duration_sec,
        },
        "speed_response": samples,
        "identified_dynamics": {
            "steady_gain_rpm_per_percent": steady_gain_rpm_per_percent,
            "time_constant_sec": time_constant_sec,
            "fit_rmse_rpm": fit_rmse_rpm,
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
