#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path


ROOT = Path("/root")
OUTPUT_PATH = ROOT / "reheat_loop_design.json"
CASE_PATH = ROOT / "reheat_commissioning_case.json"
SIMULATOR_PATH = ROOT / "reheat_loop_simulator.py"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_simulator():
    spec = importlib.util.spec_from_file_location("reheat_loop_simulator", SIMULATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SIM = load_simulator()
CASE_DATA = load_json(CASE_PATH)


def assert_close(actual, expected, tolerance=1e-6):
    assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"


def assert_metric_close(actual, expected):
    if expected is None:
        assert actual is None, f"expected null, got {actual}"
    else:
        assert_close(actual, expected, tolerance=1e-6)


def get_expected():
    evaluations = SIM.evaluate_candidates(CASE_DATA)
    selected = next(item for item in evaluations if item["feasible"])
    return evaluations, selected


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/reheat_loop_design.json"


def test_top_level_contract():
    data = load_json(OUTPUT_PATH)
    for field in [
        "case_id",
        "selection_rule",
        "selected_lambda_sec",
        "controller",
        "selected_metrics",
        "candidates",
        "trajectory",
        "summary",
    ]:
        assert field in data, f"missing '{field}'"

    assert data["case_id"] == CASE_DATA["case_id"]
    assert isinstance(data["selection_rule"], str) and data["selection_rule"].strip()
    assert isinstance(data["summary"], str) and data["summary"].strip()
    assert isinstance(data["candidates"], list) and len(data["candidates"]) == len(CASE_DATA["candidate_lambda_sec"])
    assert isinstance(data["trajectory"], list) and data["trajectory"], "trajectory must be non-empty"


def test_candidate_evaluations_match_simulator():
    data = load_json(OUTPUT_PATH)
    expected_evaluations, _ = get_expected()

    by_lambda = {item["lambda_sec"]: item for item in data["candidates"]}
    assert set(by_lambda) == set(CASE_DATA["candidate_lambda_sec"])

    for expected in expected_evaluations:
        actual = by_lambda[expected["lambda_sec"]]
        assert actual["feasible"] == expected["feasible"]

        for gain_name in ["Kp", "Ki", "Kd"]:
            assert_close(actual["controller"][gain_name], expected["controller"][gain_name])

        for metric_name, expected_value in expected["metrics"].items():
            assert metric_name in actual["metrics"], f"missing metric '{metric_name}' for lambda {expected['lambda_sec']}"
            assert_metric_close(actual["metrics"][metric_name], expected_value)


def test_selected_candidate_is_fastest_feasible():
    data = load_json(OUTPUT_PATH)
    expected_evaluations, expected_selected = get_expected()

    feasible_lambdas = [item["lambda_sec"] for item in expected_evaluations if item["feasible"]]
    assert feasible_lambdas, "case must contain at least one feasible candidate"
    assert data["selected_lambda_sec"] == min(feasible_lambdas)
    assert data["selected_lambda_sec"] == expected_selected["lambda_sec"]

    for gain_name in ["Kp", "Ki", "Kd"]:
        assert_close(data["controller"][gain_name], expected_selected["controller"][gain_name])

    for metric_name, expected_value in expected_selected["metrics"].items():
        assert metric_name in data["selected_metrics"], f"missing selected metric '{metric_name}'"
        assert_metric_close(data["selected_metrics"][metric_name], expected_value)


def test_selected_metrics_meet_acceptance():
    data = load_json(OUTPUT_PATH)
    metrics = data["selected_metrics"]
    acceptance = CASE_DATA["acceptance"]

    assert metrics["rise_time_sec"] is not None
    assert metrics["rise_time_sec"] <= acceptance["max_rise_time_sec"]
    assert metrics["overshoot_percent"] <= acceptance["max_overshoot_percent"]
    assert metrics["settling_time_sec"] is not None
    assert metrics["settling_time_sec"] <= acceptance["max_settling_time_sec"]
    assert metrics["saturation_ratio"] <= acceptance["max_saturation_ratio"]


def test_selected_trajectory_matches_simulator():
    data = load_json(OUTPUT_PATH)
    _, expected_selected = get_expected()
    trajectory = data["trajectory"]
    expected_trajectory = expected_selected["trajectory"]

    assert len(trajectory) == len(expected_trajectory)

    for actual, expected in zip(trajectory[:10], expected_trajectory[:10]):
        for field in ["time_sec", "zone_temp_c", "setpoint_c", "valve_percent", "error_c"]:
            assert field in actual, f"trajectory entry missing '{field}'"
            assert_close(actual[field], expected[field])

    for actual, expected in zip(trajectory[-10:], expected_trajectory[-10:]):
        for field in ["time_sec", "zone_temp_c", "setpoint_c", "valve_percent", "error_c"]:
            assert_close(actual[field], expected[field])
