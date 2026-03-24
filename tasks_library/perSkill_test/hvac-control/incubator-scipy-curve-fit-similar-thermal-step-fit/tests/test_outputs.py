#!/usr/bin/env python3

import csv
import json
import os

import numpy as np

ROOT_DIR = "/root"
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "incubator_fit_report.json")
RUN_INFO_PATH = os.path.join(ROOT_DIR, "incubator_run_info.json")
DATA_PATH = os.path.join(ROOT_DIR, "incubator_step_test.csv")
VERIFICATION_PATH = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_csv_rows(path):
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def heating_segment(rows, step_start):
    return [
        {
            "time_s": float(row["time_s"]),
            "heater_percent": float(row["heater_percent"]),
            "temperature_c": float(row["temperature_c"]),
        }
        for row in rows
        if float(row["time_s"]) >= step_start and float(row["heater_percent"]) > 0.0
    ]


def model_predictions(rows, ambient, heater_step, gain, tau, step_start):
    times = np.array([row["time_s"] - step_start for row in rows], dtype=float)
    observed = np.array([row["temperature_c"] for row in rows], dtype=float)
    predicted = ambient + gain * heater_step * (1.0 - np.exp(-times / tau))
    return observed, predicted


class TestReportStructure:
    def test_required_fields(self):
        report = load_json(REPORT_PATH)

        for field in [
            "experiment_id",
            "input_file",
            "ambient_temperature_c",
            "target_temperature_c",
            "heater_step_percent",
            "step_start_time_s",
            "samples_used",
            "model",
            "predicted_equilibrium_at_step_c",
            "required_hold_heater_percent",
        ]:
            assert field in report, f"missing '{field}'"

        for field in ["gain_c_per_percent", "time_constant_s", "r_squared", "rmse_c"]:
            assert field in report["model"], f"missing model field '{field}'"

    def test_metadata_matches_inputs(self):
        report = load_json(REPORT_PATH)
        run_info = load_json(RUN_INFO_PATH)

        assert report["experiment_id"] == run_info["experiment_id"]
        assert report["input_file"] == "incubator_step_test.csv"
        assert abs(report["ambient_temperature_c"] - run_info["ambient_temperature_c"]) < 1e-9
        assert abs(report["target_temperature_c"] - run_info["target_temperature_c"]) < 1e-9
        assert abs(report["heater_step_percent"] - run_info["heater_step_percent"]) < 1e-9
        assert abs(report["step_start_time_s"] - run_info["step_start_time_s"]) < 1e-9


class TestFitAccuracy:
    def test_parameters_close_to_true_values(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)

        gain = report["model"]["gain_c_per_percent"]
        tau = report["model"]["time_constant_s"]

        gain_error = abs(gain - truth["process_gain_K"]) / truth["process_gain_K"]
        tau_error = abs(tau - truth["time_constant_tau_s"]) / truth["time_constant_tau_s"]

        assert gain_error <= 0.08, f"gain error {gain_error * 100:.2f}% exceeds 8%"
        assert tau_error <= 0.12, f"time constant error {tau_error * 100:.2f}% exceeds 12%"

    def test_quality_metrics_reasonable(self):
        report = load_json(REPORT_PATH)
        assert report["model"]["r_squared"] >= 0.99
        assert report["model"]["rmse_c"] <= 0.25


class TestDataConsistency:
    def test_report_metrics_match_log_data(self):
        report = load_json(REPORT_PATH)
        rows = load_csv_rows(DATA_PATH)
        step_rows = heating_segment(rows, report["step_start_time_s"])

        observed, predicted = model_predictions(
            step_rows,
            report["ambient_temperature_c"],
            report["heater_step_percent"],
            report["model"]["gain_c_per_percent"],
            report["model"]["time_constant_s"],
            report["step_start_time_s"],
        )

        rmse = float(np.sqrt(np.mean((observed - predicted) ** 2)))
        ss_res = float(np.sum((observed - predicted) ** 2))
        ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
        r_squared = float(1.0 - ss_res / ss_tot)

        assert report["samples_used"] == len(step_rows)
        assert abs(report["model"]["rmse_c"] - rmse) <= 0.02
        assert abs(report["model"]["r_squared"] - r_squared) <= 0.005

    def test_equilibrium_temperature_consistent(self):
        report = load_json(REPORT_PATH)
        expected = (
            report["ambient_temperature_c"]
            + report["model"]["gain_c_per_percent"] * report["heater_step_percent"]
        )
        assert abs(report["predicted_equilibrium_at_step_c"] - expected) <= 0.05


class TestHoldRecommendation:
    def test_required_hold_percent(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)

        expected = (
            (report["target_temperature_c"] - report["ambient_temperature_c"])
            / report["model"]["gain_c_per_percent"]
        )
        relative_error = abs(
            report["required_hold_heater_percent"] - truth["expected_hold_heater_percent"]
        ) / truth["expected_hold_heater_percent"]

        assert abs(report["required_hold_heater_percent"] - expected) <= 0.05
        assert relative_error <= 0.03, f"hold setting error {relative_error * 100:.2f}% exceeds 3%"
        assert 45.0 <= report["required_hold_heater_percent"] <= 60.0
