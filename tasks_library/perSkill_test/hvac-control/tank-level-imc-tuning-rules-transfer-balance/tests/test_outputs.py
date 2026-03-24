#!/usr/bin/env python3
"""Tests for the tank level balance transfer task."""

import importlib.util
import json
import math
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
TESTS_DIR = Path(os.environ.get("TASK_TESTS_DIR", os.path.dirname(os.path.abspath(__file__))))
REPORT_PATH = ROOT_DIR / "tank_level_controller_report.json"
CASE_PATH = ROOT_DIR / "tank_level_case.json"
SIM_PATH = ROOT_DIR / "tank_level_sim.py"
CHECKPOINT_TIMES = [60.0, 120.0, 240.0, 360.0, 540.0, 720.0]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sim_module():
    spec = importlib.util.spec_from_file_location("tank_level_sim", SIM_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReportShape:
    def test_sections_exist(self):
        report = load_json(REPORT_PATH)

        for field in ["scenario", "controller", "checkpoints", "performance_summary", "balance_analysis", "assessment"]:
            assert field in report, f"missing '{field}'"

        assert isinstance(report["checkpoints"], list), "checkpoints must be a list"
        assert isinstance(report["assessment"], str) and report["assessment"].strip(), "assessment must be non-empty"


class TestScenarioAndController:
    def test_scenario_matches_case(self):
        report = load_json(REPORT_PATH)
        case = load_json(CASE_PATH)
        scenario = report["scenario"]

        required = [
            "target_level_pct",
            "initial_level_pct",
            "base_level_pct",
            "constant_outflow_equivalent_pct",
            "process_gain_pct_per_valve_pct",
            "time_constant_s",
            "duration_s",
            "dt_s",
        ]
        for field in required:
            assert field in scenario, f"scenario missing '{field}'"
            assert math.isclose(scenario[field], case[field], rel_tol=0.0, abs_tol=1e-9), \
                f"scenario.{field} does not match tank_level_case.json"

    def test_imc_pi_relation(self):
        report = load_json(REPORT_PATH)
        case = load_json(CASE_PATH)
        controller = report["controller"]

        for field in ["type", "Kp", "Ki", "Kd", "lambda_s"]:
            assert field in controller, f"controller missing '{field}'"

        assert controller["type"] == "PI", "controller.type must be 'PI'"
        assert controller["Kd"] == 0.0, "controller.Kd must be 0.0"
        assert controller["lambda_s"] > 0.0, "lambda_s must be positive"

        process_gain = case["process_gain_pct_per_valve_pct"]
        tau = case["time_constant_s"]
        expected_kp = tau / (process_gain * controller["lambda_s"])
        expected_ki = expected_kp / tau

        assert math.isclose(controller["Kp"], expected_kp, rel_tol=1e-4, abs_tol=1e-4), \
            "Kp does not match the first-order IMC PI formula"
        assert math.isclose(controller["Ki"], expected_ki, rel_tol=1e-4, abs_tol=1e-4), \
            "Ki does not match the first-order IMC PI formula"


class TestCheckpointsAndReplay:
    def test_checkpoint_times_and_fields(self):
        report = load_json(REPORT_PATH)
        checkpoints = report["checkpoints"]

        assert len(checkpoints) == len(CHECKPOINT_TIMES), "checkpoints length must match the required times"
        reported_times = [entry["time_s"] for entry in checkpoints]
        assert reported_times == CHECKPOINT_TIMES, "checkpoints must use the required times in order"

        for field in ["time_s", "level_pct", "valve_open_pct", "error_pct"]:
            assert field in checkpoints[0], f"checkpoint entries must include '{field}'"

    def test_checkpoints_match_replayed_trace(self):
        report = load_json(REPORT_PATH)
        sim_module = load_sim_module()
        controller = report["controller"]

        trace = sim_module.simulate_pi_controller(
            str(CASE_PATH),
            controller["Kp"],
            controller["Ki"],
        )
        replayed = sim_module.build_checkpoints(trace, CHECKPOINT_TIMES)

        assert replayed == report["checkpoints"], "reported checkpoints do not match simulator replay"


class TestPerformanceAndBalance:
    def test_metrics_and_balance_fields_match_recomputed_values(self):
        report = load_json(REPORT_PATH)
        case = load_json(CASE_PATH)
        sim_module = load_sim_module()
        controller = report["controller"]

        trace = sim_module.simulate_pi_controller(
            str(CASE_PATH),
            controller["Kp"],
            controller["Ki"],
        )
        metrics = sim_module.compute_metrics(
            trace,
            case["target_level_pct"],
            case["settling_band_pct"],
            case["steady_state_window_s"],
            case["dt_s"],
        )
        balance = report["balance_analysis"]
        expected_hold = round(sim_module.required_hold_valve_pct(case), 4)
        expected_average = sim_module.average_valve_pct_last_window(
            trace,
            case["steady_state_window_s"],
            case["dt_s"],
        )

        for field, value in metrics.items():
            assert field in report["performance_summary"], f"performance_summary missing '{field}'"
            assert math.isclose(report["performance_summary"][field], value, abs_tol=1e-4), \
                f"reported {field} does not match recomputed metric"

        for field in ["required_hold_valve_pct", "average_valve_pct_last_120s", "outflow_rejection_ok"]:
            assert field in balance, f"balance_analysis missing '{field}'"

        assert math.isclose(balance["required_hold_valve_pct"], expected_hold, abs_tol=1e-4), \
            "required_hold_valve_pct is incorrect"
        assert math.isclose(balance["average_valve_pct_last_120s"], expected_average, abs_tol=1e-4), \
            "average_valve_pct_last_120s is incorrect"

        expected_ok = (
            metrics["settling_time_s"] <= 320.0
            and abs(expected_average - expected_hold) <= 1.0
        )
        assert balance["outflow_rejection_ok"] == expected_ok, \
            "outflow_rejection_ok does not match the computed balance result"

    def test_performance_targets(self):
        report = load_json(REPORT_PATH)
        metrics = report["performance_summary"]
        balance = report["balance_analysis"]

        assert metrics["settling_time_s"] <= 320.0, "settling_time_s must be at most 320s"
        assert metrics["steady_state_error_pct"] <= 0.25, "steady_state_error_pct must be at most 0.25%"
        assert metrics["peak_level_pct"] < 64.5, "peak_level_pct must stay below 64.5%"
        assert metrics["minimum_level_pct"] > 49.5, "minimum_level_pct must stay above 49.5%"
        assert abs(
            balance["average_valve_pct_last_120s"] - balance["required_hold_valve_pct"]
        ) <= 1.0, "average valve position must stay close to the required hold valve position"
        assert balance["outflow_rejection_ok"] is True, "outflow_rejection_ok must be true for a valid report"
