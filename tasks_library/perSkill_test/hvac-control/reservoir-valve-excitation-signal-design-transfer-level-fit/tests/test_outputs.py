#!/usr/bin/env python3

import json
import os

import numpy as np


ROOT_DIR = os.environ.get("TASK_ROOT", "/root")
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "tank_level_response_fit.json")
PROFILE_PATH = os.path.join(ROOT_DIR, "reservoir_profile.json")
VERIFICATION_PARAMS = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def step_model(time_s, baseline_level_cm, valve_step_percent, gain_cm_per_percent, time_constant_sec):
    return baseline_level_cm + valve_step_percent * gain_cm_per_percent * (1.0 - np.exp(-time_s / time_constant_sec))


class TestReportStructure:
    def test_required_fields_exist(self):
        report = load_json(REPORT_PATH)
        for field in ["excitation_plan", "level_response", "identified_model"]:
            assert field in report, f"missing '{field}'"

        plan = report["excitation_plan"]
        for field in ["baseline_duration_sec", "valve_step_percent", "sample_interval_sec", "total_duration_sec", "overflow_limit_cm"]:
            assert field in plan, f"excitation_plan missing '{field}'"

        model = report["identified_model"]
        for field in ["steady_gain_cm_per_percent", "time_constant_sec", "fit_rmse_cm", "predicted_final_level_cm"]:
            assert field in model, f"identified_model missing '{field}'"

    def test_level_response_fields(self):
        report = load_json(REPORT_PATH)
        assert len(report["level_response"]) >= 120, "level_response should contain enough samples"
        for idx, row in enumerate(report["level_response"][:10]):
            for field in ["time_s", "level_cm", "valve_open_percent"]:
                assert field in row, f"row {idx} missing '{field}'"


class TestExcitationDesign:
    def test_single_step_protocol_and_overflow_margin(self):
        report = load_json(REPORT_PATH)
        profile = load_json(PROFILE_PATH)
        plan = report["excitation_plan"]
        data = report["level_response"]

        times = [row["time_s"] for row in data]
        levels = [row["level_cm"] for row in data]

        assert plan["valve_step_percent"] > 0.0
        assert plan["sample_interval_sec"] > 0.0
        assert abs(plan["overflow_limit_cm"] - profile["overflow_level_cm"]) < 1e-9
        assert abs(plan["total_duration_sec"] - times[-1]) <= plan["sample_interval_sec"] + 1e-9

        deltas = np.diff(times)
        assert np.all(deltas > 0.0), "timestamps must be strictly increasing"
        assert np.max(np.abs(deltas - plan["sample_interval_sec"])) < 1e-9, "sampling interval must stay fixed"

        baseline_rows = [row for row in data if row["time_s"] <= plan["baseline_duration_sec"]]
        step_rows = [row for row in data if row["time_s"] > plan["baseline_duration_sec"]]
        assert len(baseline_rows) >= 6, "need a short baseline segment before the valve step"
        assert len(step_rows) >= 100, "need enough post-step data"

        assert max(row["valve_open_percent"] for row in baseline_rows) == 0.0, "baseline must stay at 0% valve opening"

        step_levels = {round(row["valve_open_percent"], 6) for row in step_rows}
        assert len(step_levels) == 1, "post-step valve command must stay constant"
        assert abs(step_rows[0]["valve_open_percent"] - plan["valve_step_percent"]) < 1e-9

        assert 16.0 <= plan["baseline_duration_sec"] <= 40.0
        assert 4.0 <= plan["sample_interval_sec"] <= 6.0
        assert 480.0 <= plan["total_duration_sec"] <= 720.0
        assert 24.0 <= plan["valve_step_percent"] <= 44.0

        peak_level = max(levels)
        assert peak_level < plan["overflow_limit_cm"], "level exceeded the overflow limit"
        assert plan["overflow_limit_cm"] - peak_level >= 3.0, "test should preserve at least 3 cm overflow headroom"

        baseline_level = float(np.mean([row["level_cm"] for row in baseline_rows]))
        late_level = float(np.mean([row["level_cm"] for row in step_rows[-10:]]))
        assert late_level - baseline_level >= 6.0, "step response is too small for reliable identification"

    def test_report_is_self_consistent(self):
        report = load_json(REPORT_PATH)
        plan = report["excitation_plan"]
        model = report["identified_model"]
        data = report["level_response"]

        baseline_rows = [row for row in data if row["time_s"] <= plan["baseline_duration_sec"]]
        baseline_level = float(np.mean([row["level_cm"] for row in baseline_rows]))
        expected_final_level = baseline_level + plan["valve_step_percent"] * model["steady_gain_cm_per_percent"]

        assert model["steady_gain_cm_per_percent"] > 0.0
        assert 80.0 <= model["time_constant_sec"] <= 320.0
        assert model["fit_rmse_cm"] >= 0.0
        assert abs(model["predicted_final_level_cm"] - expected_final_level) <= 0.35, "predicted final level is inconsistent"


class TestIdentificationAccuracy:
    def test_identified_parameters_are_accurate(self):
        report = load_json(REPORT_PATH)
        model = report["identified_model"]
        truth = load_json(VERIFICATION_PARAMS)

        gain_error = abs(model["steady_gain_cm_per_percent"] - truth["gain_cm_per_percent"]) / truth["gain_cm_per_percent"]
        tau_error = abs(model["time_constant_sec"] - truth["time_constant_sec"]) / truth["time_constant_sec"]

        assert gain_error <= 0.10, f"gain error {gain_error * 100:.1f}% exceeds 10%"
        assert tau_error <= 0.15, f"time constant error {tau_error * 100:.1f}% exceeds 15%"
        assert model["fit_rmse_cm"] <= 0.2, f"fit RMSE {model['fit_rmse_cm']:.3f}cm exceeds 0.2cm"

    def test_model_matches_level_response(self):
        report = load_json(REPORT_PATH)
        model = report["identified_model"]
        data = report["level_response"]
        plan = report["excitation_plan"]

        baseline_rows = [row for row in data if row["time_s"] <= plan["baseline_duration_sec"]]
        step_rows = [row for row in data if row["time_s"] > plan["baseline_duration_sec"]]

        baseline_level = float(np.mean([row["level_cm"] for row in baseline_rows]))
        t0 = step_rows[0]["time_s"]
        t_rel = np.array([row["time_s"] - t0 for row in step_rows], dtype=float)
        observed = np.array([row["level_cm"] for row in step_rows], dtype=float)
        predicted = step_model(
            t_rel,
            baseline_level,
            plan["valve_step_percent"],
            model["steady_gain_cm_per_percent"],
            model["time_constant_sec"],
        )
        rmse = float(np.sqrt(np.mean((observed - predicted) ** 2)))
        assert abs(rmse - model["fit_rmse_cm"]) <= 0.03, "reported RMSE is inconsistent with raw data"
