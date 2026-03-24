#!/usr/bin/env python3

import csv
import json
import math
import os
from pathlib import Path

import numpy as np


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = ROOT_DIR / "mixing_tank_fit.json"
MANIFEST_PATH = ROOT_DIR / "mixing_run_manifest.json"
TRACE_PATH = ROOT_DIR / "outlet_concentration_trace.tsv"


def load_json(path):
    with path.open() as f:
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


def split_trace():
    manifest = load_json(MANIFEST_PATH)
    rows = load_rows()
    step_start = float(manifest["step_start_s"])
    pre_rows = [row for row in rows if row["elapsed_s"] < step_start]
    post_rows = [row for row in rows if row["elapsed_s"] >= step_start]
    baseline = float(np.mean([row["outlet_concentration_g_per_l"] for row in pre_rows]))
    times = np.array([row["elapsed_s"] - step_start for row in post_rows], dtype=float)
    concentrations = np.array([row["outlet_concentration_g_per_l"] for row in post_rows], dtype=float)
    return manifest, baseline, times, concentrations


def fit_reference_model(times, concentrations, baseline, step_amplitude):
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


def observed_crossing_time(times, concentrations, threshold):
    if concentrations[0] >= threshold:
        return float(times[0])

    for idx in range(1, len(times)):
        if concentrations[idx] >= threshold:
            t0 = float(times[idx - 1])
            t1 = float(times[idx])
            c0 = float(concentrations[idx - 1])
            c1 = float(concentrations[idx])
            if c1 == c0:
                return t1
            fraction = (threshold - c0) / (c1 - c0)
            return t0 + fraction * (t1 - t0)
    return None


class TestMixingTankFit:
    def test_output_exists_and_structure(self):
        manifest = load_json(MANIFEST_PATH)
        output = load_json(OUTPUT_PATH)

        assert output["trial_id"] == manifest["trial_id"]
        assert output["log_file"] == manifest["samples_file"]
        assert output["valve_step_percent_open"] == manifest["valve_step_percent_open"]
        assert isinstance(output["baseline_concentration_g_per_l"], (int, float))

        fitted = output["fitted_model"]
        for field in [
            "gain_g_per_l_per_pct_open",
            "tau_s",
            "steady_state_concentration_g_per_l",
            "r_squared",
            "rmse_g_per_l",
        ]:
            assert field in fitted
            assert isinstance(fitted[field], (int, float))

        window = output["qualification_window"]
        assert window["target_band_g_per_l"] == manifest["target_band_g_per_l"]
        for field in ["time_to_enter_band_s", "time_to_leave_band_s", "time_in_band_s"]:
            assert field in window
            assert isinstance(window[field], (int, float))

    def test_baseline_matches_pre_step_samples(self):
        output = load_json(OUTPUT_PATH)
        _, baseline, _, _ = split_trace()

        assert abs(output["baseline_concentration_g_per_l"] - baseline) <= 0.01

    def test_fitted_model_matches_trace(self):
        output = load_json(OUTPUT_PATH)
        manifest, baseline, times, concentrations = split_trace()
        step_amplitude = float(manifest["valve_step_percent_open"])
        fitted = output["fitted_model"]

        predicted = baseline + fitted["gain_g_per_l_per_pct_open"] * step_amplitude * (1.0 - np.exp(-times / fitted["tau_s"]))
        residuals = concentrations - predicted
        rmse = float(np.sqrt(np.mean((residuals) ** 2)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((concentrations - np.mean(concentrations)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        assert abs(fitted["rmse_g_per_l"] - rmse) <= 0.005
        assert abs(fitted["r_squared"] - r_squared) <= 0.002
        assert fitted["r_squared"] >= 0.995
        assert fitted["rmse_g_per_l"] <= 0.08
        expected_steady = baseline + fitted["gain_g_per_l_per_pct_open"] * step_amplitude
        assert abs(fitted["steady_state_concentration_g_per_l"] - expected_steady) <= 0.01

    def test_fit_is_close_to_reference_solution(self):
        output = load_json(OUTPUT_PATH)
        manifest, baseline, times, concentrations = split_trace()
        step_amplitude = float(manifest["valve_step_percent_open"])
        reference = fit_reference_model(times, concentrations, baseline, step_amplitude)
        fitted = output["fitted_model"]

        assert abs(fitted["gain_g_per_l_per_pct_open"] - reference["gain_g_per_l_per_pct_open"]) / reference["gain_g_per_l_per_pct_open"] <= 0.04
        assert abs(fitted["tau_s"] - reference["tau_s"]) / reference["tau_s"] <= 0.06
        assert abs(fitted["steady_state_concentration_g_per_l"] - reference["steady_state_concentration_g_per_l"]) <= 0.03
        assert abs(fitted["r_squared"] - reference["r_squared"]) <= 0.002
        assert abs(fitted["rmse_g_per_l"] - reference["rmse_g_per_l"]) <= 0.005

    def test_qualification_window_is_consistent(self):
        output = load_json(OUTPUT_PATH)
        _, baseline, times, concentrations = split_trace()
        fitted = output["fitted_model"]
        window = output["qualification_window"]
        target_min, target_max = window["target_band_g_per_l"]

        expected_enter = predicted_crossing_time(
            baseline,
            fitted["steady_state_concentration_g_per_l"],
            fitted["tau_s"],
            float(target_min),
        )
        expected_leave = predicted_crossing_time(
            baseline,
            fitted["steady_state_concentration_g_per_l"],
            fitted["tau_s"],
            float(target_max),
        )
        observed_enter = observed_crossing_time(times, concentrations, float(target_min))
        observed_leave = observed_crossing_time(times, concentrations, float(target_max))

        assert abs(window["time_to_enter_band_s"] - expected_enter) <= 0.01
        assert abs(window["time_to_leave_band_s"] - expected_leave) <= 0.01
        assert abs(window["time_in_band_s"] - (expected_leave - expected_enter)) <= 0.01
        assert observed_enter is not None
        assert observed_leave is not None
        assert abs(window["time_to_enter_band_s"] - observed_enter) <= 3.5
        assert abs(window["time_to_leave_band_s"] - observed_leave) <= 3.5
        assert window["time_to_enter_band_s"] > 0.0
        assert window["time_to_leave_band_s"] > window["time_to_enter_band_s"]
        assert window["time_in_band_s"] > 0.0
