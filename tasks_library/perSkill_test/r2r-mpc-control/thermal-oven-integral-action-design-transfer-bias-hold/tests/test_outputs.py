#!/usr/bin/env python3

import json
import math
import os
import sys

import numpy as np

ROOT_DIR = "/root"
if not os.path.exists(os.path.join(ROOT_DIR, "heater_controller_scaffold.py")):
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "environment"))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from heater_controller_scaffold import evaluate_config, run_baseline_case, run_case
from thermal_oven_env import load_case_library, load_model_bundle


OUTPUT_PATH = os.path.join("/root", "heater_integrator_config.json")
if not os.path.exists(OUTPUT_PATH):
    OUTPUT_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "heater_integrator_config.json")
    )


def load_output():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_top_level_contract():
    payload = load_output()
    assert set(payload.keys()) == {
        "integral_gain_by_zone",
        "leak_by_zone",
        "integral_limit_by_zone",
    }

    for key in payload:
        values = payload[key]
        assert isinstance(values, list), f"{key} must be a list"
        assert len(values) == 2, f"{key} must have exactly 2 entries"
        assert all(isinstance(value, (int, float)) for value in values)

    assert min(payload["integral_gain_by_zone"]) > 0.0
    assert 0.0 < min(payload["leak_by_zone"]) <= max(payload["leak_by_zone"]) <= 1.0
    assert min(payload["integral_limit_by_zone"]) > 0.0


def test_case_library_matches_instruction():
    cases = load_case_library()["cases"]
    assert set(cases.keys()) == {"load_swap_recovery", "ambient_bias_hold"}


def test_closed_loop_metrics_meet_targets():
    payload = load_output()
    results = evaluate_config(payload)
    power_limits = np.array(load_model_bundle()["heater_power_limit_kw"], dtype=float)

    for case_id, metrics in results.items():
        assert metrics["tail_mean_abs_error"] < 0.15, f"{case_id} tail mean error too large"
        assert metrics["tail_max_abs_error"] < 0.23, f"{case_id} tail max error too large"
        improvement = metrics["baseline_tail_mean_abs_error"] - metrics["tail_mean_abs_error"]
        assert improvement >= 0.12, f"{case_id} did not improve the baseline enough"
        assert metrics["peak_temperature_c"] < 176.0, f"{case_id} peak temperature too large"
        assert (
            metrics["peak_heater_power_kw"] <= float(np.max(power_limits)) + 1e-9
        ), f"{case_id} heater power exceeded the declared limit"


def test_baseline_metric_matches_scaffold_definition():
    payload = load_output()
    results = evaluate_config(payload)
    for case_id in results:
        _, baseline_metrics = run_baseline_case(case_id)
        assert math.isclose(
            results[case_id]["baseline_tail_mean_abs_error"],
            baseline_metrics["tail_mean_abs_error"],
            rel_tol=0.0,
            abs_tol=1e-12,
        )


def test_trace_contract_and_integral_clipping():
    payload = load_output()
    case_library = load_case_library()["cases"]

    for case_id, case_def in case_library.items():
        trace, metrics = run_case(case_id, payload)
        assert len(trace) == int(case_def["duration_steps"])

        previous_time = 0.0
        for entry in trace:
            assert set(entry.keys()) == {
                "time_sec",
                "temperatures_c",
                "reference_temperatures_c",
                "heater_power_kw",
                "integral_state_kw",
                "load_kw",
            }
            assert len(entry["temperatures_c"]) == 2
            assert len(entry["reference_temperatures_c"]) == 2
            assert len(entry["heater_power_kw"]) == 2
            assert len(entry["integral_state_kw"]) == 2
            assert len(entry["load_kw"]) == 2
            assert entry["time_sec"] > previous_time
            previous_time = entry["time_sec"]

            integral_state = np.abs(np.array(entry["integral_state_kw"], dtype=float))
            limits = np.array(payload["integral_limit_by_zone"], dtype=float)
            assert np.all(integral_state <= limits + 1e-9)

        recomputed_tail_mean = metrics["tail_mean_abs_error"]
        assert recomputed_tail_mean < 0.15
