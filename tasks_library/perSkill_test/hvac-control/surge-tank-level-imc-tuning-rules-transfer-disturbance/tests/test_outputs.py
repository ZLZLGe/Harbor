#!/usr/bin/env python3

import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = ROOT / "surge_tank_level_report.json"
CASE_PATH = ROOT / "surge_tank_case.json"
SCHEDULE_PATH = ROOT / "disturbance_schedule.csv"
SIMULATOR_PATH = ROOT / "surge_tank_simulator.py"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_module(path):
    spec = importlib.util.spec_from_file_location("surge_tank_simulator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SIM = load_module(SIMULATOR_PATH)
CASE_DATA = load_json(CASE_PATH)
SCHEDULE = SIM.load_schedule(SCHEDULE_PATH)
EVALUATIONS = SIM.evaluate_candidates(CASE_DATA, SCHEDULE)
FEASIBLE = [item for item in EVALUATIONS if item["meets_constraints"]]
SELECTED = max(FEASIBLE, key=lambda item: item["lambda_min"])
EXPECTED_TRACE = SIM.run_closed_loop(CASE_DATA, SCHEDULE, SELECTED["lambda_min"])
EXPECTED_METRICS = SIM.summarize_trajectory(CASE_DATA, SCHEDULE, EXPECTED_TRACE)
DISTURBANCE_CLEAR = SIM.disturbance_clear_time(SCHEDULE)


def assert_close(actual, expected, tolerance=1e-6):
    assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"


def assert_optional_close(actual, expected):
    if expected is None:
        assert actual is None, f"expected null, got {actual}"
    else:
        assert actual is not None, "expected a numeric value"
        assert_close(actual, expected)


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/surge_tank_level_report.json"


def test_top_level_contract():
    data = load_json(OUTPUT_PATH)

    for field in [
        "case_id",
        "selection_rule",
        "process_model",
        "selected_lambda_min",
        "controller",
        "selected_metrics",
        "candidate_review",
        "recovery_trace",
        "stability_report",
        "summary",
    ]:
        assert field in data, f"missing '{field}'"

    assert data["case_id"] == CASE_DATA["case_id"]
    assert isinstance(data["selection_rule"], str) and data["selection_rule"].strip()
    assert isinstance(data["summary"], str) and data["summary"].strip()
    assert isinstance(data["candidate_review"], list)
    assert len(data["candidate_review"]) == len(CASE_DATA["candidate_lambda_min"])
    assert isinstance(data["recovery_trace"], list) and data["recovery_trace"], "recovery_trace must be non-empty"

    for key in ["K", "tau_min"]:
        assert_close(data["process_model"][key], CASE_DATA["process_model"][key])


def test_candidate_review_matches_simulator():
    data = load_json(OUTPUT_PATH)
    review_by_lambda = {item["lambda_min"]: item for item in data["candidate_review"]}
    assert set(review_by_lambda) == set(CASE_DATA["candidate_lambda_min"])

    for expected in EVALUATIONS:
        actual = review_by_lambda[expected["lambda_min"]]
        assert actual["meets_constraints"] == expected["meets_constraints"]

        for gain_name, gain_value in expected["controller"].items():
            assert_close(actual["controller"][gain_name], gain_value)

        for metric_name, metric_value in expected["metrics"].items():
            assert metric_name in actual["metrics"], f"missing metric '{metric_name}'"
            assert_optional_close(actual["metrics"][metric_name], metric_value)


def test_selected_lambda_is_largest_feasible_candidate():
    data = load_json(OUTPUT_PATH)

    assert FEASIBLE, "case must include at least one feasible candidate"
    assert_close(data["selected_lambda_min"], SELECTED["lambda_min"])

    for gain_name, gain_value in SELECTED["controller"].items():
        assert_close(data["controller"][gain_name], gain_value)

    for metric_name, metric_value in EXPECTED_METRICS.items():
        assert metric_name in data["selected_metrics"], f"missing selected metric '{metric_name}'"
        assert_optional_close(data["selected_metrics"][metric_name], metric_value)


def test_recovery_trace_matches_selected_simulation():
    data = load_json(OUTPUT_PATH)
    trace = data["recovery_trace"]

    assert len(trace) == len(EXPECTED_TRACE)

    for actual, expected in zip(trace[:12], EXPECTED_TRACE[:12]):
        for field in [
            "time_min",
            "level_percent",
            "setpoint_percent",
            "valve_percent",
            "disturbance_percent",
            "error_percent",
        ]:
            assert field in actual, f"trace entry missing '{field}'"
            assert_close(actual[field], expected[field])

    for actual, expected in zip(trace[-12:], EXPECTED_TRACE[-12:]):
        for field in [
            "time_min",
            "level_percent",
            "setpoint_percent",
            "valve_percent",
            "disturbance_percent",
            "error_percent",
        ]:
            assert_close(actual[field], expected[field])


def test_stability_report_is_consistent():
    data = load_json(OUTPUT_PATH)
    acceptance = CASE_DATA["acceptance"]
    report = data["stability_report"]

    for field in [
        "disturbance_clear_time_min",
        "within_band_at_end",
        "meets_recovery_deadline",
        "meets_rebound_limit",
        "narrative",
    ]:
        assert field in report, f"missing stability report field '{field}'"

    assert_close(report["disturbance_clear_time_min"], DISTURBANCE_CLEAR)
    assert report["within_band_at_end"] == (
        abs(EXPECTED_METRICS["final_error_percent"]) <= acceptance["stability_band_percent"]
    )
    assert report["meets_recovery_deadline"] == (
        EXPECTED_METRICS["recovery_time_min"] is not None
        and EXPECTED_METRICS["recovery_time_min"] <= acceptance["max_recovery_time_after_disturbance_min"]
    )
    assert report["meets_rebound_limit"] == (
        EXPECTED_METRICS["peak_rebound_above_setpoint_percent"]
        <= acceptance["max_rebound_above_setpoint_percent"]
    )
    assert isinstance(report["narrative"], str) and report["narrative"].strip()
