#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
cd "$ROOT_DIR"

python3 <<'PY'
import json
import math
import os
from pathlib import Path

import numpy as np


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
EVENT_PATH = ROOT / "dc_bus_event.json"
SAMPLES_PATH = ROOT / "voltage_recovery_samples.jsonl"
OUTPUT_PATH = ROOT / "dc_bus_fit.json"


def load_event():
    with EVENT_PATH.open() as f:
        return json.load(f)


def load_samples():
    rows = []
    with SAMPLES_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def fit_step_response(times, voltages, baseline, released_load):
    observed_delta = max(float(voltages[-1] - baseline), 0.5)
    gain_guess = observed_delta / released_load
    gain_min = max(0.01, 0.7 * gain_guess)
    gain_max = max(gain_min + 0.05, 1.3 * gain_guess)
    tau_min = 1.0
    tau_max = max(12.0, 0.6 * float(times[-1]))

    def evaluate(gain, tau):
        predicted = baseline + gain * released_load * (1.0 - np.exp(-times / tau))
        residuals = voltages - predicted
        return float(np.sqrt(np.mean(residuals ** 2)))

    best_rmse = None
    best_gain = None
    best_tau = None

    for gain in np.linspace(gain_min, gain_max, 240):
        for tau in np.linspace(tau_min, tau_max, 260):
            rmse = evaluate(gain, tau)
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    refine_gain_min = max(0.01, best_gain * 0.9)
    refine_gain_max = best_gain * 1.1
    refine_tau_min = max(0.5, best_tau * 0.85)
    refine_tau_max = best_tau * 1.15

    for gain in np.linspace(refine_gain_min, refine_gain_max, 300):
        for tau in np.linspace(refine_tau_min, refine_tau_max, 320):
            rmse = evaluate(gain, tau)
            if rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    predicted = baseline + best_gain * released_load * (1.0 - np.exp(-times / best_tau))
    residuals = voltages - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((voltages - np.mean(voltages)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return best_gain, best_tau, r_squared, float(np.sqrt(np.mean(residuals ** 2)))


event = load_event()
samples = load_samples()
switch_ms = float(event["switch_event_ms"])
released_load = float(event["released_load_a"])
target_fraction = float(event["recovery_target_fraction"])

pre_event = [row for row in samples if float(row["sample_ms"]) < switch_ms]
post_event = [row for row in samples if float(row["sample_ms"]) >= switch_ms]

pre_event_voltage = float(np.mean([float(row["bus_voltage_v"]) for row in pre_event]))
times = np.array([float(row["sample_ms"]) - switch_ms for row in post_event], dtype=float)
voltages = np.array([float(row["bus_voltage_v"]) for row in post_event], dtype=float)

gain, tau_ms, r_squared, rmse_v = fit_step_response(times, voltages, pre_event_voltage, released_load)
steady_state_voltage = pre_event_voltage + gain * released_load
time_to_target_ms = float(-tau_ms * math.log(1.0 - target_fraction))
voltage_at_target_v = pre_event_voltage + target_fraction * (steady_state_voltage - pre_event_voltage)

result = {
    "event_id": event["event_id"],
    "samples_file": event["samples_file"],
    "pre_event_voltage_v": round(pre_event_voltage, 6),
    "released_load_a": released_load,
    "fitted_model": {
        "gain_v_per_a": round(gain, 6),
        "tau_ms": round(tau_ms, 6),
        "steady_state_voltage_v": round(steady_state_voltage, 6),
        "r_squared": round(r_squared, 6),
        "rmse_v": round(rmse_v, 6),
    },
    "recovery_metrics": {
        "target_fraction": target_fraction,
        "time_to_95_ms": round(time_to_target_ms, 6),
        "voltage_at_95_v": round(voltage_at_target_v, 6),
    },
}

with OUTPUT_PATH.open("w") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
