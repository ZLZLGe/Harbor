#!/usr/bin/env python3

import json
import os

import numpy as np


ROOT_DIR = os.environ.get("TASK_ROOT", "/root")
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "motor_speed_model.json")
CONFIG_PATH = os.path.join(ROOT_DIR, "motor_bench_config.json")
VERIFICATION_PARAMS = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def step_model(time_s, baseline_speed_rpm, pwm_step_percent, gain_rpm_per_percent, time_constant_sec):
    return baseline_speed_rpm + pwm_step_percent * gain_rpm_per_percent * (1.0 - np.exp(-time_s / time_constant_sec))


class TestReportStructure:
    def test_required_fields_exist(self):
        report = load_json(REPORT_PATH)
        for field in ["excitation_plan", "speed_response", "identified_dynamics"]:
            assert field in report, f"missing '{field}'"

        plan = report["excitation_plan"]
        for field in ["baseline_duration_sec", "pwm_step_percent", "sample_interval_sec", "total_duration_sec"]:
            assert field in plan, f"excitation_plan missing '{field}'"

        model = report["identified_dynamics"]
        for field in ["steady_gain_rpm_per_percent", "time_constant_sec", "fit_rmse_rpm"]:
            assert field in model, f"identified_dynamics missing '{field}'"

    def test_speed_response_fields(self):
        report = load_json(REPORT_PATH)
        assert len(report["speed_response"]) >= 80, "speed_response should contain enough samples"
        for idx, row in enumerate(report["speed_response"][:10]):
            for field in ["time_s", "speed_rpm", "pwm_percent"]:
                assert field in row, f"row {idx} missing '{field}'"


class TestExcitationDesign:
    def test_single_step_protocol_and_limits(self):
        report = load_json(REPORT_PATH)
        config = load_json(CONFIG_PATH)
        plan = report["excitation_plan"]
        data = report["speed_response"]

        times = [row["time_s"] for row in data]
        speeds = [row["speed_rpm"] for row in data]
        pwm_values = [row["pwm_percent"] for row in data]

        assert plan["pwm_step_percent"] > 0.0
        assert plan["sample_interval_sec"] > 0.0
        assert abs(plan["total_duration_sec"] - times[-1]) <= plan["sample_interval_sec"] + 1e-9

        deltas = np.diff(times)
        assert np.all(deltas > 0.0), "timestamps must be strictly increasing"
        assert np.max(np.abs(deltas - plan["sample_interval_sec"])) < 1e-9, "sampling interval must stay fixed"

        baseline_rows = [row for row in data if row["time_s"] <= plan["baseline_duration_sec"]]
        step_rows = [row for row in data if row["time_s"] > plan["baseline_duration_sec"]]

        assert len(baseline_rows) >= 6, "need a short baseline segment before the PWM step"
        assert len(step_rows) >= 60, "need enough post-step data"
        assert max(row["pwm_percent"] for row in baseline_rows) == 0.0, "baseline must stay at 0% PWM"

        step_levels = {round(row["pwm_percent"], 6) for row in step_rows}
        assert len(step_levels) == 1, "post-step PWM command must stay constant"
        assert abs(step_rows[0]["pwm_percent"] - plan["pwm_step_percent"]) < 1e-9

        assert 0.2 <= plan["baseline_duration_sec"] <= 0.6
        assert 0.01 <= plan["sample_interval_sec"] <= 0.05
        assert 1.8 <= plan["total_duration_sec"] <= 4.0
        assert 20.0 <= plan["pwm_step_percent"] <= 45.0

        assert max(speeds) < config["safe_speed_limit_rpm"], "speed exceeded the safety limit"
        baseline_speed = float(np.mean([row["speed_rpm"] for row in baseline_rows]))
        late_speed = float(np.mean([row["speed_rpm"] for row in step_rows[-10:]]))
        assert late_speed - baseline_speed >= 500.0, "step response is too small for reliable identification"

    def test_report_is_self_consistent(self):
        report = load_json(REPORT_PATH)
        model = report["identified_dynamics"]

        assert model["steady_gain_rpm_per_percent"] > 0.0
        assert 0.1 <= model["time_constant_sec"] <= 1.5
        assert model["fit_rmse_rpm"] >= 0.0


class TestIdentificationAccuracy:
    def test_identified_parameters_are_accurate(self):
        report = load_json(REPORT_PATH)
        model = report["identified_dynamics"]
        truth = load_json(VERIFICATION_PARAMS)

        gain_error = abs(model["steady_gain_rpm_per_percent"] - truth["gain_rpm_per_percent"]) / truth["gain_rpm_per_percent"]
        tau_error = abs(model["time_constant_sec"] - truth["time_constant_sec"]) / truth["time_constant_sec"]

        assert gain_error <= 0.10, f"gain error {gain_error * 100:.1f}% exceeds 10%"
        assert tau_error <= 0.15, f"time constant error {tau_error * 100:.1f}% exceeds 15%"
        assert model["fit_rmse_rpm"] <= 20.0, f"fit RMSE {model['fit_rmse_rpm']:.2f}rpm exceeds 20rpm"

    def test_model_matches_speed_response(self):
        report = load_json(REPORT_PATH)
        model = report["identified_dynamics"]
        data = report["speed_response"]

        plan = report["excitation_plan"]
        baseline_rows = [row for row in data if row["time_s"] <= plan["baseline_duration_sec"]]
        step_rows = [row for row in data if row["time_s"] > plan["baseline_duration_sec"]]

        baseline_speed = float(np.mean([row["speed_rpm"] for row in baseline_rows]))
        t0 = step_rows[0]["time_s"]
        t_rel = np.array([row["time_s"] - t0 for row in step_rows], dtype=float)
        observed = np.array([row["speed_rpm"] for row in step_rows], dtype=float)
        predicted = step_model(
            t_rel,
            baseline_speed,
            plan["pwm_step_percent"],
            model["steady_gain_rpm_per_percent"],
            model["time_constant_sec"],
        )
        rmse = float(np.sqrt(np.mean((observed - predicted) ** 2)))
        assert abs(rmse - model["fit_rmse_rpm"]) <= 1.0, "reported RMSE is inconsistent with raw data"
