#!/usr/bin/env python3

import json
import os

import numpy as np


ROOT_DIR = os.environ.get("TASK_ROOT", "/root")
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "incubator_identification_report.json")
VERIFICATION_PARAMS = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def step_model(time_s, baseline_temp_c, heater_step_percent, gain_c_per_percent, time_constant_sec):
    return baseline_temp_c + heater_step_percent * gain_c_per_percent * (1.0 - np.exp(-time_s / time_constant_sec))


class TestReportStructure:
    def test_required_fields_exist(self):
        report = load_json(REPORT_PATH)
        for field in [
            "heater_step_percent",
            "sample_interval_sec",
            "step_start_time_sec",
            "test_duration_sec",
            "safety_limit_c",
            "raw_response",
            "identified_model",
        ]:
            assert field in report, f"missing '{field}'"

        model = report["identified_model"]
        for field in ["gain_c_per_percent", "time_constant_sec", "fit_rmse_c"]:
            assert field in model, f"identified_model missing '{field}'"

    def test_raw_response_fields(self):
        report = load_json(REPORT_PATH)
        assert len(report["raw_response"]) >= 40, "raw_response should contain enough samples"
        for idx, row in enumerate(report["raw_response"][:10]):
            for field in ["time_s", "temperature_c", "heater_percent"]:
                assert field in row, f"row {idx} missing '{field}'"


class TestExcitationDesign:
    def test_single_step_protocol_and_timing(self):
        report = load_json(REPORT_PATH)
        data = report["raw_response"]

        times = [row["time_s"] for row in data]
        temps = [row["temperature_c"] for row in data]
        powers = [row["heater_percent"] for row in data]

        assert report["heater_step_percent"] > 0.0
        assert report["sample_interval_sec"] > 0.0
        assert abs(report["test_duration_sec"] - times[-1]) <= report["sample_interval_sec"] + 1e-6

        deltas = np.diff(times)
        assert np.all(deltas > 0.0), "timestamps must be strictly increasing"
        assert np.max(np.abs(deltas - report["sample_interval_sec"])) < 1e-6, "sampling interval must stay fixed"

        step_start = report["step_start_time_sec"]
        baseline_rows = [row for row in data if row["time_s"] <= step_start]
        step_rows = [row for row in data if row["time_s"] > step_start]
        assert len(baseline_rows) >= 3, "need a short baseline segment before the step"
        assert len(step_rows) >= 30, "need enough post-step data"

        assert max(row["heater_percent"] for row in baseline_rows) == 0.0, "baseline must stay at 0% heater"

        step_levels = {round(row["heater_percent"], 6) for row in step_rows}
        assert len(step_levels) == 1, "post-step heater command must stay constant"
        assert abs(step_rows[0]["heater_percent"] - report["heater_step_percent"]) < 1e-6

        assert max(temps) < report["safety_limit_c"], "temperature exceeded the declared safety limit"
        baseline_temp = float(np.mean([row["temperature_c"] for row in baseline_rows]))
        late_temp = float(np.mean([row["temperature_c"] for row in step_rows[-5:]]))
        assert late_temp - baseline_temp >= 1.5, "step response is too small to identify the thermal gain reliably"

    def test_report_is_self_consistent(self):
        report = load_json(REPORT_PATH)
        model = report["identified_model"]

        assert 5.0 <= report["sample_interval_sec"] <= 10.0
        assert 15.0 <= report["step_start_time_sec"] <= 40.0
        assert 300.0 <= report["test_duration_sec"] <= 700.0
        assert 15.0 <= report["heater_step_percent"] <= 40.0

        assert model["gain_c_per_percent"] > 0.0
        assert model["time_constant_sec"] > 0.0
        assert model["fit_rmse_c"] >= 0.0


class TestIdentificationAccuracy:
    def test_identified_parameters_are_accurate(self):
        report = load_json(REPORT_PATH)
        model = report["identified_model"]
        truth = load_json(VERIFICATION_PARAMS)

        gain_error = abs(model["gain_c_per_percent"] - truth["gain_c_per_percent"]) / truth["gain_c_per_percent"]
        tau_error = abs(model["time_constant_sec"] - truth["time_constant_sec"]) / truth["time_constant_sec"]

        assert gain_error <= 0.12, f"gain error {gain_error * 100:.1f}% exceeds 12%"
        assert tau_error <= 0.18, f"time constant error {tau_error * 100:.1f}% exceeds 18%"
        assert model["fit_rmse_c"] <= 0.2, f"fit RMSE {model['fit_rmse_c']:.3f}C exceeds 0.2C"

    def test_model_matches_raw_response(self):
        report = load_json(REPORT_PATH)
        model = report["identified_model"]
        data = report["raw_response"]

        step_start = report["step_start_time_sec"]
        baseline_rows = [row for row in data if row["time_s"] <= step_start]
        step_rows = [row for row in data if row["time_s"] > step_start]

        baseline_temp = float(np.mean([row["temperature_c"] for row in baseline_rows]))
        t0 = step_rows[0]["time_s"]
        t_rel = np.array([row["time_s"] - t0 for row in step_rows], dtype=float)
        observed = np.array([row["temperature_c"] for row in step_rows], dtype=float)
        predicted = step_model(
            t_rel,
            baseline_temp,
            report["heater_step_percent"],
            model["gain_c_per_percent"],
            model["time_constant_sec"],
        )
        rmse = float(np.sqrt(np.mean((observed - predicted) ** 2)))
        assert abs(rmse - model["fit_rmse_c"]) <= 0.03, "reported RMSE is inconsistent with raw data"
