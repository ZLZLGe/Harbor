#!/usr/bin/env python3

import math
import os
import sys

import yaml


ROOT_DIR = "/root"
if not os.path.exists(os.path.join(ROOT_DIR, "tank_controller_scaffold.py")):
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "environment"))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from surge_tank_env import load_case_library, load_model_bundle
from tank_controller_scaffold import evaluate_report, run_baseline_case


OUTPUT_PATH = os.path.join("/root", "level_offset_report.yaml")
if not os.path.exists(OUTPUT_PATH):
    OUTPUT_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "level_offset_report.yaml")
    )


def load_output():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_top_level_contract():
    payload = load_output()
    assert set(payload.keys()) == {"controller_settings", "cases"}

    settings = payload["controller_settings"]
    assert set(settings.keys()) == {
        "integral_gain_pct_per_m",
        "integral_leak",
        "integral_limit_pct",
        "valve_max_pct",
    }
    assert settings["integral_gain_pct_per_m"] > 0.0
    assert 0.0 < settings["integral_leak"] <= 1.0
    assert settings["integral_limit_pct"] > 0.0
    assert 0.0 < settings["valve_max_pct"] <= load_model_bundle()["physical_valve_max_pct"]


def test_case_set_matches_instruction():
    payload = load_output()
    assert set(payload["cases"].keys()) == {"blend_recipe_step", "truck_fill_recovery"}


def test_checkpoint_contract():
    payload = load_output()
    case_library = load_case_library()["cases"]

    for case_id, case_payload in payload["cases"].items():
        checkpoints = case_payload["checkpoints"]
        assert len(checkpoints) == 10
        for index, checkpoint in enumerate(checkpoints, start=1):
            assert set(checkpoint.keys()) == {
                "minute",
                "level_m",
                "target_level_m",
                "valve_pct",
                "integral_state_pct",
            }
            assert math.isclose(checkpoint["minute"], float(index), rel_tol=0.0, abs_tol=1e-9)

        assert math.isclose(
            checkpoints[-1]["minute"],
            float(case_library[case_id]["duration_min"]),
            rel_tol=0.0,
            abs_tol=1e-9,
        )


def test_report_replays_exactly():
    payload = load_output()
    replayed = evaluate_report(payload)

    for key in payload["controller_settings"]:
        assert math.isclose(
            float(payload["controller_settings"][key]),
            float(replayed["controller_settings"][key]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )

    for case_id, case_payload in payload["cases"].items():
        replayed_case = replayed["cases"][case_id]
        assert set(case_payload.keys()) == {
            "baseline_tail_mean_abs_level_error_m",
            "tail_mean_abs_level_error_m",
            "tail_max_abs_level_error_m",
            "recovery_time_min",
            "peak_overshoot_m",
            "peak_valve_pct",
            "checkpoints",
        }

        for key in (
            "baseline_tail_mean_abs_level_error_m",
            "tail_mean_abs_level_error_m",
            "tail_max_abs_level_error_m",
            "peak_overshoot_m",
            "peak_valve_pct",
        ):
            assert math.isclose(
                float(case_payload[key]),
                float(replayed_case[key]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )

        if replayed_case["recovery_time_min"] is None:
            assert case_payload["recovery_time_min"] is None
        else:
            assert math.isclose(
                float(case_payload["recovery_time_min"]),
                float(replayed_case["recovery_time_min"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )

        assert len(case_payload["checkpoints"]) == len(replayed_case["checkpoints"])
        for original, replay in zip(case_payload["checkpoints"], replayed_case["checkpoints"]):
            for field in original:
                assert math.isclose(
                    float(original[field]),
                    float(replay[field]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ), f"{case_id} checkpoint mismatch in field {field}"


def test_baseline_metric_matches_nominal_controller():
    payload = load_output()
    for case_id, case_payload in payload["cases"].items():
        _, baseline_metrics, _ = run_baseline_case(case_id)
        assert math.isclose(
            float(case_payload["baseline_tail_mean_abs_level_error_m"]),
            float(baseline_metrics["tail_mean_abs_level_error_m"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )


def test_performance_targets():
    payload = load_output()
    valve_limit = float(payload["controller_settings"]["valve_max_pct"])

    for case_id, case_payload in payload["cases"].items():
        assert case_payload["tail_mean_abs_level_error_m"] < 0.020
        assert case_payload["tail_max_abs_level_error_m"] < 0.030
        improvement = (
            case_payload["baseline_tail_mean_abs_level_error_m"]
            - case_payload["tail_mean_abs_level_error_m"]
        )
        assert improvement >= 0.240, f"{case_id} did not improve enough"
        assert case_payload["recovery_time_min"] is not None
        assert case_payload["recovery_time_min"] <= 5.6
        assert case_payload["peak_overshoot_m"] < 0.040
        assert case_payload["peak_valve_pct"] <= valve_limit + 1e-12
