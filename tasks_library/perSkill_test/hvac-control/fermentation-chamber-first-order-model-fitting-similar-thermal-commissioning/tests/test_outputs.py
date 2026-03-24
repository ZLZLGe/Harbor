#!/usr/bin/env python3

import csv
import json
import math
import os
from pathlib import Path

import numpy as np


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = ROOT_DIR / "fermentation_model_fit.json"
PROFILE_PATH = ROOT_DIR / "chamber_profile.json"
LOG_PATH = ROOT_DIR / "heating_step_log.csv"


def load_json(path):
    with path.open() as f:
        return json.load(f)


def load_rows():
    with LOG_PATH.open(newline="") as f:
        return [
            {
                "elapsed_min": float(row["elapsed_min"]),
                "heater_power_pct": float(row["heater_power_pct"]),
                "temperature_c": float(row["temperature_c"]),
            }
            for row in csv.DictReader(f)
        ]


def split_log(rows):
    idle_rows = [row for row in rows if row["heater_power_pct"] == 0.0]
    step_rows = [row for row in rows if row["heater_power_pct"] > 0.0]
    ambient = float(np.mean([row["temperature_c"] for row in idle_rows]))
    step_start = step_rows[0]["elapsed_min"]
    times = np.array([row["elapsed_min"] - step_start for row in step_rows], dtype=float)
    temps = np.array([row["temperature_c"] for row in step_rows], dtype=float)
    heater_power = float(step_rows[0]["heater_power_pct"])
    return ambient, times, temps, heater_power


def fit_reference_model(times, temps, ambient, heater_power):
    observed_delta = max(temps[-1] - ambient, 0.5)
    k_guess = observed_delta / heater_power
    k_min = max(0.01, 0.5 * k_guess)
    k_max = max(k_min + 0.02, 1.5 * k_guess)
    tau_min = 1.0
    tau_max = max(8.0, 3.0 * times[-1])

    def rmse_for(k, tau):
        predicted = ambient + k * heater_power * (1.0 - np.exp(-times / tau))
        return float(np.sqrt(np.mean((temps - predicted) ** 2)))

    best_rmse = None
    best_k = None
    best_tau = None

    for k in np.linspace(k_min, k_max, 240):
        for tau in np.linspace(tau_min, tau_max, 240):
            rmse = rmse_for(k, tau)
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_k = float(k)
                best_tau = float(tau)

    for k in np.linspace(max(0.01, best_k * 0.85), best_k * 1.15, 320):
        for tau in np.linspace(max(0.5, best_tau * 0.75), best_tau * 1.25, 320):
            rmse = rmse_for(k, tau)
            if rmse < best_rmse:
                best_rmse = rmse
                best_k = float(k)
                best_tau = float(tau)

    predicted = ambient + best_k * heater_power * (1.0 - np.exp(-times / best_tau))
    residuals = temps - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((temps - np.mean(temps)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse_c = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "K": best_k,
        "tau_min": best_tau,
        "r_squared": r_squared,
        "rmse_c": rmse_c,
    }


def predicted_minutes(ambient, gain_k, heater_power, tau_min, target_c):
    ratio = 1.0 - (target_c - ambient) / (gain_k * heater_power)
    return float(-tau_min * math.log(ratio))


def relative_error(actual, expected):
    return abs(actual - expected) / abs(expected)


class TestFermentationModelFit:
    def test_output_exists_and_structure(self):
        output = load_json(OUTPUT_PATH)
        profile = load_json(PROFILE_PATH)

        assert output["batch_id"] == profile["batch_id"]
        assert output["log_file"] == profile["step_log_file"]
        assert isinstance(output["ambient_temperature_c"], (int, float))
        assert output["heater_power_percent"] == profile["heater_power_percent"]

        fitted = output["fitted_model"]
        for field in ["K", "tau_min", "r_squared", "rmse_c"]:
            assert field in fitted
            assert isinstance(fitted[field], (int, float))

        predictions = output["predictions"]
        assert predictions["target_band_c"] == profile["target_band_c"]
        for field in [
            "minutes_from_step_to_target_min",
            "minutes_from_step_to_target_midpoint",
            "minutes_from_step_to_target_max",
        ]:
            assert field in predictions
            assert isinstance(predictions[field], (int, float))

    def test_model_matches_log(self):
        rows = load_rows()
        output = load_json(OUTPUT_PATH)
        ambient, times, temps, heater_power = split_log(rows)

        assert abs(output["ambient_temperature_c"] - ambient) <= 0.1

        fitted = output["fitted_model"]
        predicted = ambient + fitted["K"] * heater_power * (1.0 - np.exp(-times / fitted["tau_min"]))
        residuals = temps - predicted
        rmse_c = float(np.sqrt(np.mean(residuals ** 2)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((temps - np.mean(temps)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        assert abs(fitted["rmse_c"] - rmse_c) <= 0.02
        assert abs(fitted["r_squared"] - r_squared) <= 0.01
        assert fitted["r_squared"] >= 0.98
        assert fitted["rmse_c"] <= 0.12

    def test_fit_is_close_to_reference(self):
        rows = load_rows()
        output = load_json(OUTPUT_PATH)
        ambient, times, temps, heater_power = split_log(rows)
        reference = fit_reference_model(times, temps, ambient, heater_power)
        fitted = output["fitted_model"]

        assert relative_error(fitted["K"], reference["K"]) <= 0.08
        assert relative_error(fitted["tau_min"], reference["tau_min"]) <= 0.10
        assert abs(fitted["r_squared"] - reference["r_squared"]) <= 0.01
        assert abs(fitted["rmse_c"] - reference["rmse_c"]) <= 0.02

    def test_predictions_are_consistent(self):
        output = load_json(OUTPUT_PATH)
        rows = load_rows()
        ambient, _, _, heater_power = split_log(rows)
        fitted = output["fitted_model"]
        predictions = output["predictions"]
        band_min, band_max = predictions["target_band_c"]
        midpoint = (band_min + band_max) / 2.0

        expected_min = predicted_minutes(ambient, fitted["K"], heater_power, fitted["tau_min"], band_min)
        expected_mid = predicted_minutes(ambient, fitted["K"], heater_power, fitted["tau_min"], midpoint)
        expected_max = predicted_minutes(ambient, fitted["K"], heater_power, fitted["tau_min"], band_max)

        assert abs(predictions["minutes_from_step_to_target_min"] - expected_min) <= 0.2
        assert abs(predictions["minutes_from_step_to_target_midpoint"] - expected_mid) <= 0.2
        assert abs(predictions["minutes_from_step_to_target_max"] - expected_max) <= 0.2
        assert predictions["minutes_from_step_to_target_min"] < predictions["minutes_from_step_to_target_midpoint"]
        assert predictions["minutes_from_step_to_target_midpoint"] < predictions["minutes_from_step_to_target_max"]

    def test_predictions_are_close_to_reference(self):
        output = load_json(OUTPUT_PATH)
        rows = load_rows()
        ambient, times, temps, heater_power = split_log(rows)
        reference = fit_reference_model(times, temps, ambient, heater_power)
        band_min, band_max = output["predictions"]["target_band_c"]
        midpoint = (band_min + band_max) / 2.0

        ref_min = predicted_minutes(ambient, reference["K"], heater_power, reference["tau_min"], band_min)
        ref_mid = predicted_minutes(ambient, reference["K"], heater_power, reference["tau_min"], midpoint)
        ref_max = predicted_minutes(ambient, reference["K"], heater_power, reference["tau_min"], band_max)

        assert abs(output["predictions"]["minutes_from_step_to_target_min"] - ref_min) <= 0.8
        assert abs(output["predictions"]["minutes_from_step_to_target_midpoint"] - ref_mid) <= 0.8
        assert abs(output["predictions"]["minutes_from_step_to_target_max"] - ref_max) <= 0.8
