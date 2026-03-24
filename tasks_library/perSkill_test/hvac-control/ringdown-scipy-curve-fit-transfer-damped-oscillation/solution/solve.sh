#!/bin/bash
set -e

cd /root

python3 <<'PY'
import json
import math
from pathlib import Path

import numpy as np

INPUT_PATH = Path("/root/beam_ringdown_case.json")
OUTPUT_PATH = Path("/root/ringdown_modal_fit.json")


def ringdown_model(time_s, amplitude, decay_rate, damped_frequency_hz, phase_rad, offset_g):
    return offset_g + amplitude * np.exp(-decay_rate * time_s) * np.sin(
        2.0 * math.pi * damped_frequency_hz * time_s + phase_rad
    )


def solve_linearized(time_s, accel_g, freq_guess_hz):
    def search(decay_grid, freq_grid):
        best = None
        ones = np.ones_like(time_s)
        for decay_rate in decay_grid:
            envelope = np.exp(-decay_rate * time_s)
            for damped_frequency_hz in freq_grid:
                angle = 2.0 * math.pi * damped_frequency_hz * time_s
                design = np.column_stack(
                    [
                        envelope * np.sin(angle),
                        envelope * np.cos(angle),
                        ones,
                    ]
                )
                coeffs, _, _, _ = np.linalg.lstsq(design, accel_g, rcond=None)
                predicted = design @ coeffs
                sse = float(np.sum((accel_g - predicted) ** 2))
                if best is None or sse < best[0]:
                    best = (sse, decay_rate, damped_frequency_hz, coeffs)
        return best

    coarse_decay = np.linspace(0.1, 4.0, 120)
    coarse_freq = np.linspace(max(1.0, freq_guess_hz - 4.0), freq_guess_hz + 4.0, 220)
    _, coarse_decay_rate, coarse_freq_hz, _ = search(coarse_decay, coarse_freq)

    fine_decay = np.linspace(max(0.05, coarse_decay_rate - 0.3), coarse_decay_rate + 0.3, 321)
    fine_freq = np.linspace(max(1.0, coarse_freq_hz - 0.4), coarse_freq_hz + 0.4, 401)
    _, decay_rate, damped_frequency_hz, coeffs = search(fine_decay, fine_freq)

    sin_coeff, cos_coeff, offset_g = coeffs
    amplitude = float(np.hypot(sin_coeff, cos_coeff))
    phase_rad = float(math.atan2(cos_coeff, sin_coeff))
    return amplitude, float(decay_rate), float(damped_frequency_hz), phase_rad, float(offset_g)


def fit_ringdown(time_s, accel_g):
    tail_count = max(10, len(accel_g) // 5)
    offset_guess = float(np.mean(accel_g[-tail_count:]))
    centered = accel_g - offset_guess
    amplitude_guess = float(np.max(np.abs(centered)))
    dt = float(np.mean(np.diff(time_s)))
    freqs = np.fft.rfftfreq(len(time_s), d=dt)
    spectrum = np.abs(np.fft.rfft(centered))
    if spectrum.size:
        spectrum[0] = 0.0
    freq_guess_hz = float(freqs[np.argmax(spectrum)]) if len(freqs) > 1 else 1.0
    freq_guess_hz = min(30.0, max(1.0, freq_guess_hz))

    try:
        from scipy.optimize import curve_fit
    except ImportError:
        curve_fit = None

    if curve_fit is None:
        return solve_linearized(time_s, accel_g, freq_guess_hz)

    initial_guesses = [
        [amplitude_guess, 1.0, freq_guess_hz, 0.0, offset_guess],
        [amplitude_guess, 0.6, freq_guess_hz, 0.8, offset_guess],
        [amplitude_guess, 1.8, freq_guess_hz, -0.8, offset_guess],
    ]
    bounds = ([0.0, 0.0, 1.0, -math.pi, -0.2], [5.0, 10.0, 30.0, math.pi, 0.2])

    best = None
    for p0 in initial_guesses:
        try:
            popt, _ = curve_fit(
                ringdown_model,
                time_s,
                accel_g,
                p0=p0,
                bounds=bounds,
                maxfev=50000,
            )
            predicted = ringdown_model(time_s, *popt)
            sse = float(np.sum((accel_g - predicted) ** 2))
            if best is None or sse < best[0]:
                best = (sse, popt)
        except RuntimeError:
            continue

    if best is None:
        return solve_linearized(time_s, accel_g, freq_guess_hz)

    return [float(value) for value in best[1]]


with INPUT_PATH.open("r") as f:
    case = json.load(f)

observations = case["observations"]
time_s = np.array([row["time_s"] for row in observations], dtype=float)
accel_g = np.array([row["acceleration_g"] for row in observations], dtype=float)

amplitude, decay_rate, damped_frequency_hz, phase_rad, offset_g = fit_ringdown(time_s, accel_g)
predicted = ringdown_model(time_s, amplitude, decay_rate, damped_frequency_hz, phase_rad, offset_g)

omega_d = 2.0 * math.pi * damped_frequency_hz
omega_n = math.sqrt(decay_rate ** 2 + omega_d ** 2)
natural_frequency_hz = omega_n / (2.0 * math.pi)
damping_ratio = decay_rate / omega_n
log_decrement = 2.0 * math.pi * damping_ratio / math.sqrt(1.0 - damping_ratio ** 2)

residuals = accel_g - predicted
rmse_g = float(np.sqrt(np.mean(residuals ** 2)))
ss_res = float(np.sum(residuals ** 2))
ss_tot = float(np.sum((accel_g - np.mean(accel_g)) ** 2))
r_squared = float(1.0 - ss_res / ss_tot)

minimum_required = float(case["minimum_required_damping_ratio"])
evaluation_time_s = float(case["evaluation_time_s"])
amplitude_limit_g = float(case["amplitude_limit_g"])
predicted_envelope = float(amplitude * math.exp(-decay_rate * evaluation_time_s))
time_to_amplitude_limit = float(math.log(amplitude / amplitude_limit_g) / decay_rate)
threshold_margin = float(damping_ratio - minimum_required)
meets_requirement = bool(damping_ratio >= minimum_required)

report = {
    "inspection_id": case["inspection_id"],
    "input_file": "beam_ringdown_case.json",
    "beam_serial": case["beam_serial"],
    "sensor_axis": case["sensor_axis"],
    "samples_used": len(observations),
    "fit_model": {
        "initial_envelope_amplitude_g": float(amplitude),
        "decay_rate_per_s": float(decay_rate),
        "damped_frequency_hz": float(damped_frequency_hz),
        "phase_rad": float(phase_rad),
        "offset_g": float(offset_g),
        "natural_frequency_hz": float(natural_frequency_hz),
        "damping_ratio": float(damping_ratio),
        "log_decrement": float(log_decrement),
        "rmse_g": float(rmse_g),
        "r_squared": float(r_squared),
    },
    "inspection_assessment": {
        "minimum_required_damping_ratio": minimum_required,
        "threshold_margin": float(threshold_margin),
        "evaluation_time_s": evaluation_time_s,
        "predicted_envelope_at_evaluation_g": predicted_envelope,
        "amplitude_limit_g": amplitude_limit_g,
        "time_to_amplitude_limit_s": time_to_amplitude_limit,
        "meets_damping_requirement": meets_requirement,
        "inspection_outcome": "pass" if meets_requirement else "fail",
    },
}

with OUTPUT_PATH.open("w") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY
