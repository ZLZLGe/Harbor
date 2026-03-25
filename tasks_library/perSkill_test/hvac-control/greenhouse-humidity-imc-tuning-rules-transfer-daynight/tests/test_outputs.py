#!/usr/bin/env python3

import csv
import json
import math
from pathlib import Path


ROOT = Path("/root")
OUTPUT_PATH = ROOT / "humidity_controller_plan.json"
CASE_PATH = ROOT / "greenhouse_humidity_case.json"
TIMES_PATH = ROOT / "summary_minutes.csv"
HORIZON_MIN = 15.0


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_times():
    with open(TIMES_PATH, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [float(row["time_min"]) for row in reader]


CASE_DATA = load_json(CASE_PATH)
SUMMARY_TIMES = load_times()
PROCESS = CASE_DATA["process_model"]


def assert_close(actual, expected, tolerance=1e-6):
    assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"


def expected_lambda(mode_name):
    candidates = CASE_DATA["modes"][mode_name]["lambda_candidates_min"]
    return min(candidates) if mode_name == "day" else max(candidates)


def expected_controller(lambda_min):
    K = PROCESS["K"]
    tau_min = PROCESS["tau_min"]
    return {
        "Kp": tau_min / (K * lambda_min),
        "Ki": 1.0 / (K * lambda_min),
        "Kd": 0.0,
    }


def expected_response(mode_name):
    mode_data = CASE_DATA["modes"][mode_name]
    lambda_min = expected_lambda(mode_name)
    initial = mode_data["initial_humidity_percent"]
    target = mode_data["target_humidity_percent"]

    samples = []
    for time_min in SUMMARY_TIMES:
        predicted = target - (target - initial) * math.exp(-time_min / lambda_min)
        samples.append(
            {
                "time_min": time_min,
                "predicted_humidity_percent": predicted,
                "error_to_target_percent": target - predicted,
            }
        )

    return {
        "duration_min": HORIZON_MIN,
        "samples": samples,
        "end_humidity_percent": samples[-1]["predicted_humidity_percent"],
        "remaining_error_percent": samples[-1]["error_to_target_percent"],
        "progress_percent_at_horizon": (1.0 - math.exp(-HORIZON_MIN / lambda_min)) * 100.0,
    }


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/humidity_controller_plan.json"


def test_top_level_contract():
    data = load_json(OUTPUT_PATH)

    for field in ["case_id", "selection_rule", "process_model", "day_mode", "night_mode", "summary"]:
        assert field in data, f"missing '{field}'"

    assert data["case_id"] == CASE_DATA["case_id"]
    assert isinstance(data["selection_rule"], str) and data["selection_rule"].strip()
    assert isinstance(data["summary"], str) and data["summary"].strip()
    assert isinstance(data["process_model"], dict)

    for field in ["K", "tau_min"]:
        assert field in data["process_model"], f"missing process field '{field}'"
        assert_close(data["process_model"][field], PROCESS[field])


def test_lambda_selection_and_gains():
    data = load_json(OUTPUT_PATH)

    for mode_name in ["day", "night"]:
        mode_output = data[f"{mode_name}_mode"]
        lambda_min = expected_lambda(mode_name)
        controller = expected_controller(lambda_min)

        assert_close(mode_output["selected_lambda_min"], lambda_min)
        for gain_name, expected_value in controller.items():
            assert gain_name in mode_output["controller"], f"missing gain '{gain_name}' in {mode_name}_mode"
            assert_close(mode_output["controller"][gain_name], expected_value)


def test_response_summaries_match_formula():
    data = load_json(OUTPUT_PATH)

    for mode_name in ["day", "night"]:
        expected = expected_response(mode_name)
        summary = data[f"{mode_name}_mode"]["response_summary"]

        assert_close(summary["duration_min"], HORIZON_MIN)
        assert isinstance(summary["samples"], list)
        assert len(summary["samples"]) == len(SUMMARY_TIMES)

        for actual_sample, expected_sample in zip(summary["samples"], expected["samples"]):
            for field in ["time_min", "predicted_humidity_percent", "error_to_target_percent"]:
                assert field in actual_sample, f"missing '{field}' in {mode_name} samples"
                assert_close(actual_sample[field], expected_sample[field])

        assert_close(summary["end_humidity_percent"], expected["end_humidity_percent"])
        assert_close(summary["remaining_error_percent"], expected["remaining_error_percent"])
        assert_close(summary["progress_percent_at_horizon"], expected["progress_percent_at_horizon"])


def test_day_is_faster_and_night_is_more_conservative():
    data = load_json(OUTPUT_PATH)

    day_lambda = data["day_mode"]["selected_lambda_min"]
    night_lambda = data["night_mode"]["selected_lambda_min"]
    assert day_lambda < night_lambda, "day mode should use a smaller lambda than night mode"

    day_progress = data["day_mode"]["response_summary"]["progress_percent_at_horizon"]
    night_progress = data["night_mode"]["response_summary"]["progress_percent_at_horizon"]
    assert day_progress > night_progress, "day mode should make more 15-minute progress than night mode"
