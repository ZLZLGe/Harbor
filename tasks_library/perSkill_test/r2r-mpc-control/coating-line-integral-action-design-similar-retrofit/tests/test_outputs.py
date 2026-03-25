#!/usr/bin/env python3

import json
import math
import os
import sys

import numpy as np

ROOT_DIR = "/root"
if not os.path.exists(os.path.join(ROOT_DIR, "coating_line_env.py")):
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "environment"))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from coating_line_env import load_case_library, summarize_trace
from controller_scaffold import NominalPredictiveController, run_baseline_case, run_case


OUTPUT_PATH = os.path.join("/root", "tension_retrofit_results.json")
if not os.path.exists(OUTPUT_PATH):
    OUTPUT_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tension_retrofit_results.json")
    )


def load_output():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


class RetrofittedController(NominalPredictiveController):
    def __init__(self, settings):
        super().__init__(horizon=8)
        self.settings = settings
        self.integral_state = np.zeros(4, dtype=float)

    def reset(self):
        self.integral_state[:] = 0.0

    def compute_control(self, state, state_ref, torque_ref, dt):
        nominal = super().compute_control(state, state_ref, torque_ref, dt)
        tension_error = state[:4] - state_ref[:4]
        gains = np.array(self.settings["integral_gain_by_section"], dtype=float)
        leak = np.array(self.settings["leak_by_section"], dtype=float)
        limits = np.array(self.settings["integral_limit_by_section"], dtype=float)
        torque_limits = np.array(self.settings["torque_limit_by_section"], dtype=float)

        self.integral_state = leak * self.integral_state - gains * dt * tension_error
        self.integral_state = np.clip(self.integral_state, -limits, limits)
        total = nominal + self.integral_state
        return np.clip(total, -torque_limits, torque_limits)


def replay_case(case_id, settings):
    controller = RetrofittedController(settings)
    trace = run_case(case_id, controller)
    return trace, summarize_trace(trace)


def assert_trace_matches(reported_trace, replayed_trace):
    assert len(reported_trace) == len(replayed_trace)
    for idx, (reported, replayed) in enumerate(zip(reported_trace, replayed_trace)):
        assert reported.keys() == replayed.keys()
        for key in ("tensions", "reference_tensions", "torques", "integral_state"):
            assert np.allclose(
                np.array(reported[key], dtype=float),
                np.array(replayed[key], dtype=float),
                rtol=0.0,
                atol=1e-9,
            ), f"trace mismatch at step {idx} field {key}"
        assert math.isclose(
            float(reported["time"]),
            float(replayed["time"]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ), f"trace mismatch at step {idx} field time"


def test_top_level_contract():
    result = load_output()
    assert set(result.keys()) == {"controller_settings", "cases"}

    settings = result["controller_settings"]
    for key in (
        "integral_gain_by_section",
        "leak_by_section",
        "integral_limit_by_section",
        "torque_limit_by_section",
    ):
        assert key in settings
        values = settings[key]
        assert isinstance(values, list) and len(values) == 4
        assert all(isinstance(value, (int, float)) for value in values)
        assert values[0] == values[1], f"{key} must use the same value for sections 1-2"
        assert values[2] == values[3], f"{key} must use the same value for sections 3-4"

    assert 0.0 < min(settings["leak_by_section"]) <= max(settings["leak_by_section"]) <= 1.0
    assert min(settings["integral_limit_by_section"]) > 0.0
    assert min(settings["torque_limit_by_section"]) > 0.0


def test_cases_present():
    result = load_output()
    assert set(result["cases"].keys()) == {"roll_change_step", "friction_bias_hold"}


def test_each_case_matches_declared_metrics():
    result = load_output()
    case_library = load_case_library()

    for case_id, payload in result["cases"].items():
        assert set(payload.keys()) == {
            "baseline_tail_mean_abs_error",
            "tail_mean_abs_error",
            "tail_max_abs_error",
            "peak_tension",
            "peak_abs_torque",
            "trace",
        }

        trace = payload["trace"]
        assert isinstance(trace, list) and trace, f"{case_id} trace must be non-empty"

        case_def = case_library["cases"][case_id]
        expected_steps = int(round(case_def["duration_sec"] / case_library["dt"]))
        assert len(trace) == expected_steps, f"{case_id} must log every simulation step"

        previous_time = 0.0
        for idx, entry in enumerate(trace):
            assert set(entry.keys()) == {
                "time",
                "tensions",
                "reference_tensions",
                "torques",
                "integral_state",
            }
            assert len(entry["tensions"]) == 4
            assert len(entry["reference_tensions"]) == 4
            assert len(entry["torques"]) == 4
            assert len(entry["integral_state"]) == 4

            current_time = float(entry["time"])
            assert current_time > previous_time
            previous_time = current_time

            expected_time = round((idx + 1) * case_library["dt"], 4)
            assert math.isclose(current_time, expected_time, abs_tol=1e-4)

        recomputed = summarize_trace(trace)
        assert math.isclose(
            payload["tail_mean_abs_error"],
            recomputed["tail_mean_abs_error"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            payload["tail_max_abs_error"],
            recomputed["tail_max_abs_error"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            payload["peak_tension"],
            recomputed["peak_tension"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            payload["peak_abs_torque"],
            recomputed["peak_abs_torque"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )


def test_reported_settings_replay_to_the_reported_traces():
    result = load_output()
    settings = result["controller_settings"]

    for case_id, payload in result["cases"].items():
        replayed_trace, replayed_metrics = replay_case(case_id, settings)
        assert_trace_matches(payload["trace"], replayed_trace)
        assert math.isclose(
            payload["tail_mean_abs_error"],
            replayed_metrics["tail_mean_abs_error"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            payload["tail_max_abs_error"],
            replayed_metrics["tail_max_abs_error"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            payload["peak_tension"],
            replayed_metrics["peak_tension"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            payload["peak_abs_torque"],
            replayed_metrics["peak_abs_torque"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )


def test_baseline_metric_is_grounded_in_provided_nominal_controller():
    result = load_output()
    for case_id, payload in result["cases"].items():
        _, baseline_metrics = run_baseline_case(case_id)
        assert math.isclose(
            payload["baseline_tail_mean_abs_error"],
            baseline_metrics["tail_mean_abs_error"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )


def test_performance_targets():
    result = load_output()
    torque_limits = result["controller_settings"]["torque_limit_by_section"]
    reported_limit = max(torque_limits)

    for case_id, payload in result["cases"].items():
        _, replayed_metrics = replay_case(case_id, result["controller_settings"])
        assert payload["tail_mean_abs_error"] < 0.40, f"{case_id} tail mean error too large"
        assert payload["tail_max_abs_error"] < 0.70, f"{case_id} tail max error too large"
        improvement = payload["baseline_tail_mean_abs_error"] - payload["tail_mean_abs_error"]
        assert improvement >= 0.12, f"{case_id} did not improve baseline enough"
        assert payload["peak_tension"] < 40.0, f"{case_id} peak tension too large"
        assert payload["peak_abs_torque"] <= reported_limit + 1e-9, f"{case_id} torque exceeds reported limit"
        assert replayed_metrics["tail_mean_abs_error"] < 0.40, f"{case_id} replay tail mean error too large"
        assert replayed_metrics["tail_max_abs_error"] < 0.70, f"{case_id} replay tail max error too large"
        assert replayed_metrics["peak_tension"] < 40.0, f"{case_id} replay peak tension too large"
        assert replayed_metrics["peak_abs_torque"] <= reported_limit + 1e-9, (
            f"{case_id} replay torque exceeds reported limit"
        )


def test_integral_state_respects_reported_limits():
    result = load_output()
    limits = np.array(result["controller_settings"]["integral_limit_by_section"], dtype=float)
    for case_id, payload in result["cases"].items():
        for entry in payload["trace"]:
            integral_state = np.abs(np.array(entry["integral_state"], dtype=float))
            assert np.all(integral_state <= limits + 1e-9), f"{case_id} integral state exceeds reported limit"
