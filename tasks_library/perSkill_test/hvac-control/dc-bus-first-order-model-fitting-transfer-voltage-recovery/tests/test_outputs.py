#!/usr/bin/env python3

import json
import math
import os
from pathlib import Path

import numpy as np


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = ROOT_DIR / "dc_bus_fit.json"
EVENT_PATH = ROOT_DIR / "dc_bus_event.json"
SAMPLES_PATH = ROOT_DIR / "voltage_recovery_samples.jsonl"


def load_json(path):
    with path.open() as f:
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


def split_samples():
    event = load_json(EVENT_PATH)
    switch_ms = float(event["switch_event_ms"])
    samples = load_samples()
    pre_event = [row for row in samples if float(row["sample_ms"]) < switch_ms]
    post_event = [row for row in samples if float(row["sample_ms"]) >= switch_ms]

    baseline = float(np.mean([float(row["bus_voltage_v"]) for row in pre_event]))
    times = np.array([float(row["sample_ms"]) - switch_ms for row in post_event], dtype=float)
    voltages = np.array([float(row["bus_voltage_v"]) for row in post_event], dtype=float)
    return event, baseline, times, voltages


def fit_reference_model(times, voltages, baseline, released_load):
    observed_delta = max(float(voltages[-1] - baseline), 0.5)
    gain_guess = observed_delta / released_load
    gain_min = max(0.01, 0.7 * gain_guess)
    gain_max = max(gain_min + 0.05, 1.3 * gain_guess)
    tau_min = 1.0
    tau_max = max(12.0, 0.6 * float(times[-1]))

    best_rmse = None
    best_gain = None
    best_tau = None

    for gain in np.linspace(gain_min, gain_max, 240):
        for tau in np.linspace(tau_min, tau_max, 260):
            predicted = baseline + gain * released_load * (1.0 - np.exp(-times / tau))
            rmse = float(np.sqrt(np.mean((voltages - predicted) ** 2)))
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    for gain in np.linspace(max(0.01, best_gain * 0.9), best_gain * 1.1, 300):
        for tau in np.linspace(max(0.5, best_tau * 0.85), best_tau * 1.15, 320):
            predicted = baseline + gain * released_load * (1.0 - np.exp(-times / tau))
            rmse = float(np.sqrt(np.mean((voltages - predicted) ** 2)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_gain = float(gain)
                best_tau = float(tau)

    predicted = baseline + best_gain * released_load * (1.0 - np.exp(-times / best_tau))
    residuals = voltages - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((voltages - np.mean(voltages)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "gain_v_per_a": best_gain,
        "tau_ms": best_tau,
        "steady_state_voltage_v": baseline + best_gain * released_load,
        "r_squared": r_squared,
        "rmse_v": rmse,
    }


def observed_crossing_time(times, voltages, threshold):
    if voltages[0] >= threshold:
        return float(times[0])

    for idx in range(1, len(times)):
        if voltages[idx] >= threshold:
            t0 = float(times[idx - 1])
            t1 = float(times[idx])
            v0 = float(voltages[idx - 1])
            v1 = float(voltages[idx])
            if v1 == v0:
                return t1
            fraction = (threshold - v0) / (v1 - v0)
            return t0 + fraction * (t1 - t0)
    return None


class TestDcBusFit:
    def test_output_exists_and_structure(self):
        event = load_json(EVENT_PATH)
        output = load_json(OUTPUT_PATH)

        assert output["event_id"] == event["event_id"]
        assert output["samples_file"] == event["samples_file"]
        assert output["released_load_a"] == event["released_load_a"]
        assert isinstance(output["pre_event_voltage_v"], (int, float))

        fitted = output["fitted_model"]
        for field in ["gain_v_per_a", "tau_ms", "steady_state_voltage_v", "r_squared", "rmse_v"]:
            assert field in fitted
            assert isinstance(fitted[field], (int, float))

        metrics = output["recovery_metrics"]
        for field in ["target_fraction", "time_to_95_ms", "voltage_at_95_v"]:
            assert field in metrics
            assert isinstance(metrics[field], (int, float))

    def test_pre_event_voltage_matches_samples(self):
        output = load_json(OUTPUT_PATH)
        event, baseline, _, _ = split_samples()

        assert abs(output["pre_event_voltage_v"] - baseline) <= 0.01
        assert output["recovery_metrics"]["target_fraction"] == event["recovery_target_fraction"]

    def test_fitted_model_matches_waveform(self):
        output = load_json(OUTPUT_PATH)
        event, baseline, times, voltages = split_samples()
        released_load = float(event["released_load_a"])
        fitted = output["fitted_model"]

        predicted = baseline + fitted["gain_v_per_a"] * released_load * (1.0 - np.exp(-times / fitted["tau_ms"]))
        residuals = voltages - predicted
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((voltages - np.mean(voltages)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        assert abs(fitted["rmse_v"] - rmse) <= 0.005
        assert abs(fitted["r_squared"] - r_squared) <= 0.002
        assert fitted["r_squared"] >= 0.995
        assert fitted["rmse_v"] <= 0.05
        assert abs(fitted["steady_state_voltage_v"] - (baseline + fitted["gain_v_per_a"] * released_load)) <= 0.01

    def test_fit_is_close_to_reference_solution(self):
        output = load_json(OUTPUT_PATH)
        event, baseline, times, voltages = split_samples()
        reference = fit_reference_model(times, voltages, baseline, float(event["released_load_a"]))
        fitted = output["fitted_model"]

        assert abs(fitted["gain_v_per_a"] - reference["gain_v_per_a"]) / reference["gain_v_per_a"] <= 0.03
        assert abs(fitted["tau_ms"] - reference["tau_ms"]) / reference["tau_ms"] <= 0.05
        assert abs(fitted["steady_state_voltage_v"] - reference["steady_state_voltage_v"]) <= 0.03
        assert abs(fitted["r_squared"] - reference["r_squared"]) <= 0.002
        assert abs(fitted["rmse_v"] - reference["rmse_v"]) <= 0.005

    def test_recovery_metrics_are_consistent(self):
        output = load_json(OUTPUT_PATH)
        event, baseline, times, voltages = split_samples()
        fitted = output["fitted_model"]
        metrics = output["recovery_metrics"]

        expected_time = -fitted["tau_ms"] * math.log(1.0 - metrics["target_fraction"])
        expected_voltage = baseline + metrics["target_fraction"] * (fitted["steady_state_voltage_v"] - baseline)
        observed_time = observed_crossing_time(times, voltages, metrics["voltage_at_95_v"])

        assert abs(metrics["time_to_95_ms"] - expected_time) <= 0.01
        assert abs(metrics["voltage_at_95_v"] - expected_voltage) <= 0.01
        assert observed_time is not None
        assert abs(metrics["time_to_95_ms"] - observed_time) <= 1.5
        assert metrics["voltage_at_95_v"] < fitted["steady_state_voltage_v"]
        assert metrics["time_to_95_ms"] > 0.0
