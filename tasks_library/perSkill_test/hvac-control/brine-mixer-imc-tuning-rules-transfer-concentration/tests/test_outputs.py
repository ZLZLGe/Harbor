#!/usr/bin/env python3
"""Tests for the brine mixer concentration-control transfer task."""

import importlib.util
import json
import math
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
TESTS_DIR = Path(os.environ.get("TASK_TESTS_DIR", os.path.dirname(os.path.abspath(__file__))))
SUMMARY_PATH = ROOT_DIR / "brine_mixer_control_summary.json"
CASE_PATH = ROOT_DIR / "brine_mixer_case.json"
SIM_PATH = ROOT_DIR / "brine_mixer_sim.py"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sim_module():
    spec = importlib.util.spec_from_file_location("brine_mixer_sim", SIM_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSummaryShape:
    def test_sections_exist(self):
        summary = load_json(SUMMARY_PATH)

        for field in [
            "scenario",
            "mixing_event",
            "controller",
            "sampled_response",
            "phase_summary",
            "blend_assessment",
        ]:
            assert field in summary, f"missing '{field}'"

        assert isinstance(summary["sampled_response"], list), "sampled_response must be a list"
        assert summary["sampled_response"], "sampled_response must not be empty"
        assert isinstance(summary["blend_assessment"], str) and summary["blend_assessment"].strip(), \
            "blend_assessment must be non-empty"


class TestScenarioAndEvent:
    def test_values_match_case(self):
        summary = load_json(SUMMARY_PATH)
        case = load_json(CASE_PATH)

        scenario = summary["scenario"]
        event = summary["mixing_event"]

        scenario_fields = [
            "target_concentration_pct",
            "initial_concentration_pct",
            "base_concentration_pct",
            "nominal_brine_valve_pct",
            "process_gain_pct_per_valve_pct",
            "time_constant_s",
            "duration_s",
            "dt_s",
        ]
        for field in scenario_fields:
            assert field in scenario, f"scenario missing '{field}'"
            assert math.isclose(scenario[field], case[field], rel_tol=0.0, abs_tol=1e-9), \
                f"scenario.{field} does not match brine_mixer_case.json"

        event_fields = ["flush_start_s", "flush_end_s", "dilution_shift_pct"]
        for field in event_fields:
            assert field in event, f"mixing_event missing '{field}'"
            assert math.isclose(event[field], case[field], rel_tol=0.0, abs_tol=1e-9), \
                f"mixing_event.{field} does not match brine_mixer_case.json"


class TestControllerDesign:
    def test_imc_pi_relation(self):
        summary = load_json(SUMMARY_PATH)
        case = load_json(CASE_PATH)
        controller = summary["controller"]

        for field in ["type", "Kp", "Ki", "Kd", "lambda_s", "bias_valve_pct"]:
            assert field in controller, f"controller missing '{field}'"

        assert controller["type"] == "PI", "controller.type must be 'PI'"
        assert controller["Kd"] == 0.0, "controller.Kd must be 0.0"
        assert controller["lambda_s"] > 0.0, "controller.lambda_s must be positive"
        assert math.isclose(
            controller["bias_valve_pct"],
            case["nominal_brine_valve_pct"],
            rel_tol=0.0,
            abs_tol=1e-9,
        ), "controller.bias_valve_pct must match the nominal brine valve bias"

        expected_kp = case["time_constant_s"] / (
            case["process_gain_pct_per_valve_pct"] * controller["lambda_s"]
        )
        expected_ki = expected_kp / case["time_constant_s"]

        assert math.isclose(controller["Kp"], expected_kp, rel_tol=0.0, abs_tol=1e-4), \
            "Kp does not match the first-order IMC PI formula"
        assert math.isclose(controller["Ki"], expected_ki, rel_tol=0.0, abs_tol=1e-4), \
            "Ki does not match the first-order IMC PI formula"


class TestSampledResponse:
    def test_sample_times_and_fields(self):
        summary = load_json(SUMMARY_PATH)
        case = load_json(CASE_PATH)
        sampled_response = summary["sampled_response"]

        expected_times = case["sample_times_s"]
        assert [entry["time_s"] for entry in sampled_response] == expected_times, \
            "sampled_response must use the required sample times"

        for field in [
            "time_s",
            "concentration_pct",
            "brine_valve_pct",
            "dilution_active",
            "error_pct",
        ]:
            assert field in sampled_response[0], f"sampled_response entries must include '{field}'"

    def test_sampled_response_matches_replay(self):
        summary = load_json(SUMMARY_PATH)
        case = load_json(CASE_PATH)
        sim_module = load_sim_module()
        controller = summary["controller"]

        trace = sim_module.simulate_pi_controller(
            str(CASE_PATH),
            controller["Kp"],
            controller["Ki"],
        )
        expected_samples = sim_module.build_sampled_response(trace, case["sample_times_s"])

        assert summary["sampled_response"] == expected_samples, \
            "sampled_response does not match simulator replay"


class TestPhaseSummary:
    def test_phase_summary_matches_recomputed_values(self):
        summary = load_json(SUMMARY_PATH)
        sim_module = load_sim_module()
        controller = summary["controller"]
        case = sim_module.load_case(str(CASE_PATH))

        trace = sim_module.simulate_pi_controller(
            str(CASE_PATH),
            controller["Kp"],
            controller["Ki"],
        )
        expected_summary = sim_module.compute_phase_summary(trace, case)

        reported = summary["phase_summary"]
        for field, value in expected_summary.items():
            assert field in reported, f"phase_summary missing '{field}'"
            assert math.isclose(reported[field], value, rel_tol=0.0, abs_tol=1e-4), \
                f"phase_summary.{field} does not match recomputed value"

    def test_performance_targets(self):
        summary = load_json(SUMMARY_PATH)
        phase_summary = summary["phase_summary"]
        target = load_json(CASE_PATH)["target_concentration_pct"]

        assert phase_summary["startup_settling_time_s"] <= 95.0, \
            "startup_settling_time_s must be at most 95s"
        assert phase_summary["flush_min_concentration_pct"] >= 6.57, \
            "flush_min_concentration_pct must stay at or above 6.57%"
        assert phase_summary["post_flush_recovery_time_s"] <= 106.0, \
            "post_flush_recovery_time_s must be at most 106s"
        assert phase_summary["steady_state_error_pct"] <= 0.053, \
            "steady_state_error_pct must be at most 0.053%"
        assert phase_summary["integral_absolute_error_pct_s"] <= 58.5, \
            "integral_absolute_error_pct_s must be at most 58.5"
        assert phase_summary["max_brine_valve_pct"] <= 61.5, \
            "max_brine_valve_pct must be at most 61.5%"
        assert abs(phase_summary["final_concentration_pct"] - target) <= 0.06, \
            "final_concentration_pct must finish within 0.06% of the target"
