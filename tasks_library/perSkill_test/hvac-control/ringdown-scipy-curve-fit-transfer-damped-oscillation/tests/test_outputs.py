#!/usr/bin/env python3

import json
import math
import os

import numpy as np


ROOT_DIR = "/root"
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "ringdown_modal_fit.json")
INPUT_PATH = os.path.join(ROOT_DIR, "beam_ringdown_case.json")
VERIFICATION_PATH = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def ringdown_model(time_s, amplitude, decay_rate, damped_frequency_hz, phase_rad, offset_g):
    return offset_g + amplitude * np.exp(-decay_rate * time_s) * np.sin(
        2.0 * math.pi * damped_frequency_hz * time_s + phase_rad
    )


class TestReportStructure:
    def test_required_fields_present(self):
        report = load_json(REPORT_PATH)

        for field in [
            "inspection_id",
            "input_file",
            "beam_serial",
            "sensor_axis",
            "samples_used",
            "fit_model",
            "inspection_assessment",
        ]:
            assert field in report, f"missing '{field}'"

        for field in [
            "initial_envelope_amplitude_g",
            "decay_rate_per_s",
            "damped_frequency_hz",
            "phase_rad",
            "offset_g",
            "natural_frequency_hz",
            "damping_ratio",
            "log_decrement",
            "rmse_g",
            "r_squared",
        ]:
            assert field in report["fit_model"], f"missing fit_model field '{field}'"

        for field in [
            "minimum_required_damping_ratio",
            "threshold_margin",
            "evaluation_time_s",
            "predicted_envelope_at_evaluation_g",
            "amplitude_limit_g",
            "time_to_amplitude_limit_s",
            "meets_damping_requirement",
            "inspection_outcome",
        ]:
            assert field in report["inspection_assessment"], (
                f"missing inspection_assessment field '{field}'"
            )

    def test_metadata_matches_input(self):
        report = load_json(REPORT_PATH)
        case = load_json(INPUT_PATH)

        assert report["inspection_id"] == case["inspection_id"]
        assert report["input_file"] == "beam_ringdown_case.json"
        assert report["beam_serial"] == case["beam_serial"]
        assert report["sensor_axis"] == case["sensor_axis"]
        assert report["samples_used"] == len(case["observations"])


class TestFitAccuracy:
    def test_parameters_close_to_reference(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)
        fit = report["fit_model"]

        amplitude_error = abs(
            fit["initial_envelope_amplitude_g"] - truth["initial_envelope_amplitude_g"]
        ) / truth["initial_envelope_amplitude_g"]
        decay_error = abs(fit["decay_rate_per_s"] - truth["decay_rate_per_s"]) / truth[
            "decay_rate_per_s"
        ]
        damped_freq_error = abs(
            fit["damped_frequency_hz"] - truth["damped_frequency_hz"]
        ) / truth["damped_frequency_hz"]
        natural_freq_error = abs(
            fit["natural_frequency_hz"] - truth["natural_frequency_hz"]
        ) / truth["natural_frequency_hz"]
        damping_ratio_error = abs(
            fit["damping_ratio"] - truth["damping_ratio"]
        ) / truth["damping_ratio"]

        assert amplitude_error <= 0.06
        assert decay_error <= 0.10
        assert damped_freq_error <= 0.015
        assert natural_freq_error <= 0.015
        assert damping_ratio_error <= 0.12

    def test_fit_quality_is_reasonable(self):
        report = load_json(REPORT_PATH)
        fit = report["fit_model"]

        assert fit["rmse_g"] <= 0.02
        assert fit["r_squared"] >= 0.99


class TestDerivedMetrics:
    def test_model_equations_are_consistent(self):
        report = load_json(REPORT_PATH)
        fit = report["fit_model"]
        assessment = report["inspection_assessment"]

        omega_d = 2.0 * math.pi * fit["damped_frequency_hz"]
        omega_n = math.sqrt(fit["decay_rate_per_s"] ** 2 + omega_d ** 2)
        expected_natural_frequency = omega_n / (2.0 * math.pi)
        expected_damping_ratio = fit["decay_rate_per_s"] / omega_n
        expected_log_decrement = (
            2.0
            * math.pi
            * expected_damping_ratio
            / math.sqrt(1.0 - expected_damping_ratio ** 2)
        )
        expected_envelope = fit["initial_envelope_amplitude_g"] * math.exp(
            -fit["decay_rate_per_s"] * assessment["evaluation_time_s"]
        )
        expected_time_to_limit = math.log(
            fit["initial_envelope_amplitude_g"] / assessment["amplitude_limit_g"]
        ) / fit["decay_rate_per_s"]

        assert abs(fit["natural_frequency_hz"] - expected_natural_frequency) <= 1e-6
        assert abs(fit["damping_ratio"] - expected_damping_ratio) <= 1e-6
        assert abs(fit["log_decrement"] - expected_log_decrement) <= 1e-6
        assert (
            abs(
                assessment["predicted_envelope_at_evaluation_g"] - expected_envelope
            )
            <= 1e-6
        )
        assert abs(assessment["time_to_amplitude_limit_s"] - expected_time_to_limit) <= 1e-6

    def test_rmse_and_r_squared_match_observations(self):
        report = load_json(REPORT_PATH)
        case = load_json(INPUT_PATH)
        fit = report["fit_model"]

        times = np.array([row["time_s"] for row in case["observations"]], dtype=float)
        observed = np.array([row["acceleration_g"] for row in case["observations"]], dtype=float)
        predicted = ringdown_model(
            times,
            fit["initial_envelope_amplitude_g"],
            fit["decay_rate_per_s"],
            fit["damped_frequency_hz"],
            fit["phase_rad"],
            fit["offset_g"],
        )

        residuals = observed - predicted
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
        r_squared = float(1.0 - ss_res / ss_tot)

        assert abs(fit["rmse_g"] - rmse) <= 1e-6
        assert abs(fit["r_squared"] - r_squared) <= 1e-6


class TestInspectionAssessment:
    def test_assessment_logic_matches_input_thresholds(self):
        report = load_json(REPORT_PATH)
        case = load_json(INPUT_PATH)
        truth = load_json(VERIFICATION_PATH)
        fit = report["fit_model"]
        assessment = report["inspection_assessment"]

        assert abs(
            assessment["minimum_required_damping_ratio"]
            - case["minimum_required_damping_ratio"]
        ) <= 1e-9
        assert abs(assessment["evaluation_time_s"] - case["evaluation_time_s"]) <= 1e-9
        assert abs(assessment["amplitude_limit_g"] - case["amplitude_limit_g"]) <= 1e-9

        expected_margin = fit["damping_ratio"] - assessment["minimum_required_damping_ratio"]
        assert abs(assessment["threshold_margin"] - expected_margin) <= 1e-6
        assert assessment["meets_damping_requirement"] is True
        assert assessment["inspection_outcome"] == "pass"

        assert abs(fit["damping_ratio"] - truth["damping_ratio"]) <= 0.004
        assert (
            abs(
                assessment["predicted_envelope_at_evaluation_g"]
                - truth["predicted_envelope_at_evaluation_g"]
            )
            <= 0.01
        )
        assert abs(assessment["time_to_amplitude_limit_s"] - truth["time_to_amplitude_limit_s"]) <= 0.08
