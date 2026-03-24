#!/bin/bash
set -euo pipefail

cd "${TASK_ROOT:-/root}"

python3 <<'PY'
import csv
import json
import math
import os
from pathlib import Path

import numpy as np


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
MANIFEST_PATH = ROOT / "mixing_run_manifest.json"
TRACE_PATH = ROOT / "outlet_concentration_trace.tsv"
OUTPUT_PATH = ROOT / "mixing_tank_fit.json"


def load_manifest():
    with MANIFEST_PATH.open() as f:
        return json.load(f)


def load_rows():
    with TRACE_PATH.open(newline="") as f:
        return [
            {
                "elapsed_s": float(row["elapsed_s"]),
                "valve_percent_open": float(row["valve_percent_open"]),
                "outlet_concentration_g_per_l": float(row["outlet_concentration_g_per_l"]),
                "recirculation_flow_lpm": float(row["recirculation_flow_lpm"]),
            }
            for row in csv.DictReader(f, delimiter="\t")
        ]


def split_trace(manifest, rows):
    step_start = float(manifest["step_start_s"])
    pre_rows = [row for row in rows if row["elapsed_s"] < step_start]
    post_rows = [row for row in rows if row["elapsed_s"] >= step_start]
    baseline = float(np.mean([row["outlet_concentration_g_per_l"] for row in pre_rows]))
    times = np.array([row["elapsed_s"] - step_start for row in post_rows], dtype=float)
    concentrations = np.array([row["outlet_concentration_g_per_l"] for row in post_rows], dtype=float)
    return baseline, times, concentrations


def fit_model(times, concentrations, baseline, step_amplitude):
    observed_delta = max(float(concentrations[-1] - baseline), 0.5)
    gain_guess = observed_delta / step_amplitude
    gain_min = max(0.01, 0.5 * gain_guess)
    gain_max = max(gain_min + 0.05, 1.5 * gain_guess)
    tau_min = 5.0
    tau_max = max(30.0, 2.5 * float(times[-1]))

    best_rmse = None
    best_gain = None
    best_tau = None

    for gain in np.linspace(gain_min, gain_max, 280):
        for tau in np.linspace(tau_min, tau_max, 320):
            predicted = baseline + gain * step_amplitude * (1.0 - np.exp(-times / tau))
            rmse = float(np.sqrt(np.mean((concentrations - predicted) ** 2)))
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    for gain in np.linspace(max(0.01, best_gain * 0.9), best_gain * 1.1, 320):
        for tau in np.linspace(max(1.0, best_tau * 0.8), best_tau * 1.2, 360):
            predicted = baseline + gain * step_amplitude * (1.0 - np.exp(-times / tau))
            rmse = float(np.sqrt(np.mean((concentrations - predicted) ** 2)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    predicted = baseline + best_gain * step_amplitude * (1.0 - np.exp(-times / best_tau))
    residuals = concentrations - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((concentrations - np.mean(concentrations)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "gain_g_per_l_per_pct_open": best_gain,
        "tau_s": best_tau,
        "steady_state_concentration_g_per_l": baseline + best_gain * step_amplitude,
        "r_squared": r_squared,
        "rmse_g_per_l": float(np.sqrt(np.mean(residuals ** 2))),
    }


def predicted_crossing_time(baseline, steady_state, tau_s, target):
    ratio = 1.0 - (target - baseline) / (steady_state - baseline)
    return float(-tau_s * math.log(ratio))


manifest = load_manifest()
rows = load_rows()
baseline, times, concentrations = split_trace(manifest, rows)
step_amplitude = float(manifest["valve_step_percent_open"])
fitted_model = fit_model(times, concentrations, baseline, step_amplitude)
target_min, target_max = manifest["target_band_g_per_l"]
steady_state = fitted_model["steady_state_concentration_g_per_l"]
enter_time = predicted_crossing_time(baseline, steady_state, fitted_model["tau_s"], float(target_min))
leave_time = predicted_crossing_time(baseline, steady_state, fitted_model["tau_s"], float(target_max))

output = {
    "trial_id": manifest["trial_id"],
    "log_file": manifest["samples_file"],
    "baseline_concentration_g_per_l": baseline,
    "valve_step_percent_open": step_amplitude,
    "fitted_model": fitted_model,
    "qualification_window": {
        "target_band_g_per_l": manifest["target_band_g_per_l"],
        "time_to_enter_band_s": enter_time,
        "time_to_leave_band_s": leave_time,
        "time_in_band_s": leave_time - enter_time,
    },
}

with OUTPUT_PATH.open("w") as f:
    json.dump(output, f, indent=2)
    f.write("\n")
PY
