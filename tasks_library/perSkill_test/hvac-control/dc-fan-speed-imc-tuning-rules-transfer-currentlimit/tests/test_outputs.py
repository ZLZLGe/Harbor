#!/usr/bin/env python3

import csv
import json
import math
import os
import tomllib
from pathlib import Path


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = ROOT / "motor_speed_tuning_card.json"
CASE_PATH = ROOT / "motor_speed_case.toml"
CHECKPOINTS_PATH = ROOT / "checkpoints_ms.tsv"


def load_case():
    with open(CASE_PATH, "rb") as handle:
        return tomllib.load(handle)


def load_output():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_checkpoints_ms():
    with open(CHECKPOINTS_PATH, "r", encoding="utf-8") as handle:
        return [float(row["time_ms"]) for row in csv.DictReader(handle, delimiter="\t")]


CASE = load_case()
CHECKPOINTS_MS = load_checkpoints_ms()
PROCESS = CASE["process_model"]
OPERATING = CASE["operating_point"]
K = PROCESS["K_rpm_per_amp"]
TAU = PROCESS["tau_sec"]
INITIAL = OPERATING["initial_speed_rpm"]
TARGET = OPERATING["target_speed_rpm"]
CURRENT_LIMIT = OPERATING["current_limit_a"]
HORIZON = CASE["response_horizon_sec"]


def assert_close(actual, expected, tolerance=1e-6):
    assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"


def expected_controller(lambda_sec):
    return {
        "Kp": TAU / (K * lambda_sec),
        "Ki": 1.0 / (K * lambda_sec),
        "Kd": 0.0,
    }


def predicted_speed(lambda_sec, time_sec):
    return TARGET - (TARGET - INITIAL) * math.exp(-time_sec / lambda_sec)


def predicted_current(lambda_sec, time_sec):
    numerator = TARGET + (TARGET - INITIAL) * (TAU / lambda_sec - 1.0) * math.exp(-time_sec / lambda_sec)
    return numerator / K


def peak_current(lambda_sec):
    steady_state = TARGET / K
    startup = (INITIAL + (TARGET - INITIAL) * TAU / lambda_sec) / K
    return max(steady_state, startup)


def selected_lambda():
    feasible = [value for value in CASE["candidate_lambda_sec"] if peak_current(value) <= CURRENT_LIMIT + 1e-12]
    assert feasible, "case must include at least one feasible candidate"
    return min(feasible)


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/motor_speed_tuning_card.json"


def test_top_level_contract():
    data = load_output()

    for field in [
        "case_id",
        "selection_rule",
        "process_model",
        "operating_point",
        "selected_lambda_sec",
        "controller",
        "candidate_review",
        "tracking_summary",
        "summary",
    ]:
        assert field in data, f"missing '{field}'"

    assert data["case_id"] == CASE["case_id"]
    assert isinstance(data["selection_rule"], str) and data["selection_rule"].strip()
    assert isinstance(data["summary"], str) and data["summary"].strip()
    assert isinstance(data["candidate_review"], list)
    assert len(data["candidate_review"]) == len(CASE["candidate_lambda_sec"])

    for key in ["K_rpm_per_amp", "tau_sec"]:
        assert_close(data["process_model"][key], PROCESS[key])

    for key in ["initial_speed_rpm", "target_speed_rpm", "current_limit_a"]:
        assert_close(data["operating_point"][key], OPERATING[key])


def test_candidate_review_matches_formulas():
    data = load_output()
    review_by_lambda = {item["lambda_sec"]: item for item in data["candidate_review"]}
    assert set(review_by_lambda) == set(CASE["candidate_lambda_sec"])

    steady_state_current = TARGET / K

    for lambda_sec in CASE["candidate_lambda_sec"]:
        actual = review_by_lambda[lambda_sec]
        expected_peak = peak_current(lambda_sec)
        expected_within = expected_peak <= CURRENT_LIMIT + 1e-12

        for gain_name, expected_value in expected_controller(lambda_sec).items():
            assert_close(actual["controller"][gain_name], expected_value)

        assert_close(actual["steady_state_current_a"], steady_state_current)
        assert_close(actual["peak_current_a"], expected_peak)
        assert actual["within_current_limit"] == expected_within


def test_fastest_feasible_lambda_is_selected():
    data = load_output()
    expected_lambda = selected_lambda()

    assert_close(data["selected_lambda_sec"], expected_lambda)

    for gain_name, expected_value in expected_controller(expected_lambda).items():
        assert_close(data["controller"][gain_name], expected_value)


def test_tracking_summary_matches_selected_lambda():
    data = load_output()
    summary = data["tracking_summary"]
    lambda_sec = selected_lambda()
    expected_peak = peak_current(lambda_sec)
    expected_final_speed = predicted_speed(lambda_sec, HORIZON)
    expected_final_error = TARGET - expected_final_speed

    for field in [
        "response_horizon_sec",
        "steady_state_current_a",
        "peak_current_a",
        "current_margin_a",
        "final_speed_rpm",
        "final_error_rpm",
        "steady_state_error_rpm",
        "checkpoints",
    ]:
        assert field in summary, f"missing tracking summary field '{field}'"

    assert_close(summary["response_horizon_sec"], HORIZON)
    assert_close(summary["steady_state_current_a"], TARGET / K)
    assert_close(summary["peak_current_a"], expected_peak)
    assert_close(summary["current_margin_a"], CURRENT_LIMIT - expected_peak)
    assert_close(summary["final_speed_rpm"], expected_final_speed)
    assert_close(summary["final_error_rpm"], expected_final_error)
    assert_close(summary["steady_state_error_rpm"], 0.0)


def test_checkpoint_predictions_match_formula():
    data = load_output()
    checkpoints = data["tracking_summary"]["checkpoints"]
    lambda_sec = selected_lambda()

    assert isinstance(checkpoints, list)
    assert len(checkpoints) == len(CHECKPOINTS_MS)

    for actual, time_ms in zip(checkpoints, CHECKPOINTS_MS):
        time_sec = time_ms / 1000.0
        expected_speed = predicted_speed(lambda_sec, time_sec)
        expected_current = predicted_current(lambda_sec, time_sec)
        expected_error = TARGET - expected_speed

        for field in ["time_ms", "predicted_speed_rpm", "predicted_current_a", "tracking_error_rpm"]:
            assert field in actual, f"checkpoint missing '{field}'"

        assert_close(actual["time_ms"], time_ms)
        assert_close(actual["predicted_speed_rpm"], expected_speed)
        assert_close(actual["predicted_current_a"], expected_current)
        assert_close(actual["tracking_error_rpm"], expected_error)


def test_selected_peak_respects_current_limit():
    data = load_output()
    peak = data["tracking_summary"]["peak_current_a"]

    assert peak <= CURRENT_LIMIT + 1e-6
