#!/usr/bin/env python3

import csv
import json
import math
import os
from pathlib import Path
import tomllib

import numpy as np


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = ROOT_DIR / "fan_speed_fit.json"
PROFILE_PATH = ROOT_DIR / "fan_step_profile.toml"
TRACE_PATH = ROOT_DIR / "fan_speed_trace.csv"


def load_output():
    with OUTPUT_PATH.open() as f:
        return json.load(f)


def load_profile():
    with PROFILE_PATH.open("rb") as f:
        return tomllib.load(f)


def load_rows():
    with TRACE_PATH.open(newline="") as f:
        return [
            {
                "timestamp_s": float(row["timestamp_s"]),
                "pwm_percent": float(row["pwm_percent"]),
                "fan_speed_rpm": float(row["fan_speed_rpm"]),
            }
            for row in csv.DictReader(f)
        ]


def split_trace():
    profile = load_profile()
    rows = load_rows()
    step_time = float(profile["step_time_s"])
    pre_rows = [row for row in rows if row["timestamp_s"] < step_time]
    post_rows = [row for row in rows if row["timestamp_s"] >= step_time]
    baseline = float(np.mean([row["fan_speed_rpm"] for row in pre_rows]))
    times = np.array([row["timestamp_s"] - step_time for row in post_rows], dtype=float)
    speeds = np.array([row["fan_speed_rpm"] for row in post_rows], dtype=float)
    step_amplitude = float(profile["pwm_after_percent"] - profile["pwm_before_percent"])
    return profile, baseline, times, speeds, step_amplitude


def fit_reference_model(times, speeds, baseline, step_amplitude):
    observed_delta = max(float(speeds[-1] - baseline), 100.0)
    gain_guess = observed_delta / step_amplitude
    gain_min = max(1.0, 0.75 * gain_guess)
    gain_max = max(gain_min + 2.0, 1.25 * gain_guess)
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


def predicted_time_to_fraction(tau_s, percent):
    fraction = float(percent) / 100.0
    return float(-tau_s * math.log(1.0 - fraction))


def predicted_speed_for_fraction(baseline, steady_state, percent):
    fraction = float(percent) / 100.0
    return float(baseline + fraction * (steady_state - baseline))


def observed_crossing_time(times, speeds, threshold):
    if speeds[0] >= threshold:
        return float(times[0])

    for idx in range(1, len(times)):
        if speeds[idx] >= threshold:
            t0 = float(times[idx - 1])
            t1 = float(times[idx])
            s0 = float(speeds[idx - 1])
            s1 = float(speeds[idx])
            if s1 == s0:
                return t1
            fraction = (threshold - s0) / (s1 - s0)
            return t0 + fraction * (t1 - t0)
    return None


class TestFanSpeedFit:
    def test_output_exists_and_structure(self):
        profile = load_profile()
        output = load_output()

        assert output["run_id"] == profile["run_id"]
        assert output["samples_file"] == profile["samples_file"]
        assert isinstance(output["baseline_speed_rpm"], (int, float))
        assert output["pwm_step_percent"] == profile["pwm_after_percent"] - profile["pwm_before_percent"]

        fitted = output["fitted_model"]
        for field in [
            "gain_rpm_per_pwm_pct",
            "tau_s",
            "steady_state_speed_rpm",
            "r_squared",
            "rmse_rpm",
        ]:
            assert field in fitted
            assert isinstance(fitted[field], (int, float))

        predictions = output["response_predictions"]
        assert predictions["target_percentages_of_speed_rise"] == profile["target_percentages_of_speed_rise"]
        for field in ["time_to_targets_s", "predicted_target_speeds_rpm"]:
            assert field in predictions

    def test_baseline_and_fit_match_trace(self):
        output = load_output()
        _, baseline, times, speeds, step_amplitude = split_trace()

        assert abs(output["baseline_speed_rpm"] - baseline) <= 0.01

        fitted = output["fitted_model"]
        predicted = baseline + fitted["gain_rpm_per_pwm_pct"] * step_amplitude * (1.0 - np.exp(-times / fitted["tau_s"]))
        residuals = speeds - predicted
        rmse = float(np.sqrt(np.mean((residuals) ** 2)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((speeds - np.mean(speeds)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        assert abs(fitted["rmse_rpm"] - rmse) <= 0.01
        assert abs(fitted["r_squared"] - r_squared) <= 0.002
        assert fitted["r_squared"] >= 0.995
        assert fitted["rmse_rpm"] <= 12.0
        expected_steady = baseline + fitted["gain_rpm_per_pwm_pct"] * step_amplitude
        assert abs(fitted["steady_state_speed_rpm"] - expected_steady) <= 0.01

    def test_fit_is_close_to_reference_solution(self):
        output = load_output()
        _, baseline, times, speeds, step_amplitude = split_trace()
        reference = fit_reference_model(times, speeds, baseline, step_amplitude)
        fitted = output["fitted_model"]

        assert abs(fitted["gain_rpm_per_pwm_pct"] - reference["gain_rpm_per_pwm_pct"]) / reference["gain_rpm_per_pwm_pct"] <= 0.03
        assert abs(fitted["tau_s"] - reference["tau_s"]) / reference["tau_s"] <= 0.04
        assert abs(fitted["steady_state_speed_rpm"] - reference["steady_state_speed_rpm"]) <= 8.0
        assert abs(fitted["r_squared"] - reference["r_squared"]) <= 0.002
        assert abs(fitted["rmse_rpm"] - reference["rmse_rpm"]) <= 0.2

    def test_response_predictions_are_consistent(self):
        output = load_output()
        profile, baseline, times, speeds, _ = split_trace()
        fitted = output["fitted_model"]
        predictions = output["response_predictions"]
        steady_state = fitted["steady_state_speed_rpm"]

        for percent in profile["target_percentages_of_speed_rise"]:
            key = f"p{int(percent)}"
            expected_time = predicted_time_to_fraction(fitted["tau_s"], percent)
            expected_speed = predicted_speed_for_fraction(baseline, steady_state, percent)
            observed_time = observed_crossing_time(times, speeds, expected_speed)

            assert abs(predictions["time_to_targets_s"][key] - expected_time) <= 0.01
            assert abs(predictions["predicted_target_speeds_rpm"][key] - expected_speed) <= 0.01
            assert observed_time is not None
            tolerance = 0.8 if percent < 90.0 else 1.2
            assert abs(predictions["time_to_targets_s"][key] - observed_time) <= tolerance

        assert predictions["time_to_targets_s"]["p80"] < predictions["time_to_targets_s"]["p95"]
        assert predictions["predicted_target_speeds_rpm"]["p80"] < predictions["predicted_target_speeds_rpm"]["p95"]
