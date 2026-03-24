#!/usr/bin/env python3
"""Offline verifier for the incubator recovery task."""

import importlib.util
import json
import math
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
BUNDLE_PATH = ROOT_DIR / "incubator_controller_bundle.json"
CASE_PATH = ROOT_DIR / "incubator_case.json"
SIM_PATH = ROOT_DIR / "incubator_recovery_sim.py"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def load_sim_module():
    spec = importlib.util.spec_from_file_location("incubator_recovery_sim", SIM_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_bundle_shape(bundle):
    for field in ["scenario", "controller", "closed_loop_trace", "performance_summary", "assessment"]:
        assert field in bundle, f"missing '{field}'"

    assert isinstance(bundle["closed_loop_trace"], list), "closed_loop_trace must be a list"
    assert bundle["closed_loop_trace"], "closed_loop_trace must not be empty"
    assert isinstance(bundle["assessment"], str) and bundle["assessment"].strip(), (
        "assessment must be a non-empty string"
    )


def check_scenario(bundle, case):
    scenario = bundle["scenario"]
    required = [
        "setpoint_c",
        "initial_temp_c",
        "ambient_temp_c",
        "process_gain_c_per_percent",
        "time_constant_s",
        "duration_s",
        "dt_s",
    ]

    for field in required:
        assert field in scenario, f"scenario missing '{field}'"
        assert math.isclose(scenario[field], case[field], rel_tol=0.0, abs_tol=1e-9), (
            f"scenario.{field} does not match incubator_case.json"
        )


def check_controller(bundle, case):
    controller = bundle["controller"]
    for field in ["type", "Kp", "Ki", "Kd", "lambda_s"]:
        assert field in controller, f"controller missing '{field}'"

    assert controller["type"] == "PI", "controller.type must be 'PI'"
    assert controller["Kd"] == 0.0, "controller.Kd must be 0.0"
    assert controller["lambda_s"] > 0.0, "lambda_s must be positive"

    process_gain = case["process_gain_c_per_percent"]
    tau = case["time_constant_s"]
    expected_kp = tau / (process_gain * controller["lambda_s"])
    expected_ki = expected_kp / tau

    assert math.isclose(controller["Kp"], expected_kp, rel_tol=1e-4, abs_tol=1e-4), (
        "Kp does not match the first-order PI tuning formula"
    )
    assert math.isclose(controller["Ki"], expected_ki, rel_tol=1e-4, abs_tol=1e-4), (
        "Ki does not match the first-order PI tuning formula"
    )


def check_trace_and_metrics(bundle, case, sim_module):
    trace = bundle["closed_loop_trace"]
    for field in ["time_s", "temperature_c", "heater_power_pct", "error_c"]:
        assert field in trace[0], f"trace entries must include '{field}'"

    times = [entry["time_s"] for entry in trace]
    assert times[-1] >= 360.0, "closed_loop_trace must cover at least 360s"
    assert all(times[index] > times[index - 1] for index in range(1, len(times))), (
        "trace timestamps must be strictly increasing"
    )

    controller = bundle["controller"]
    replay_trace = sim_module.simulate_pi_controller(
        str(CASE_PATH),
        controller["Kp"],
        controller["Ki"],
    )
    assert len(replay_trace) == len(trace), "trace length mismatch"

    for expected, actual in zip(replay_trace[::20], trace[::20]):
        assert math.isclose(actual["temperature_c"], expected["temperature_c"], abs_tol=1e-4), (
            "trace temperature does not match simulator replay"
        )
        assert math.isclose(actual["heater_power_pct"], expected["heater_power_pct"], abs_tol=1e-4), (
            "trace heater power does not match simulator replay"
        )
        assert math.isclose(actual["error_c"], expected["error_c"], abs_tol=1e-4), (
            "trace error does not match simulator replay"
        )

    metrics = sim_module.compute_metrics(
        trace,
        case["setpoint_c"],
        case["settling_band_c"],
        case["steady_state_window_s"],
        case["dt_s"],
    )
    reported = bundle["performance_summary"]

    for field in [
        "settling_time_s",
        "overshoot_c",
        "steady_state_error_c",
        "peak_temperature_c",
        "final_temperature_c",
    ]:
        assert field in reported, f"performance_summary missing '{field}'"
        assert math.isclose(reported[field], metrics[field], abs_tol=1e-4), (
            f"reported {field} does not match recomputed metric"
        )

    assert reported["settling_time_s"] <= 240.0, "settling_time_s must be at most 240s"
    assert reported["steady_state_error_c"] <= 0.15, "steady_state_error_c must be at most 0.15C"
    assert reported["peak_temperature_c"] < 37.5, "peak_temperature_c must stay below 37.5C"
    assert reported["final_temperature_c"] <= 37.1, "final_temperature_c must not stay above 37.1C"


def main():
    bundle = load_json(BUNDLE_PATH)
    case = load_json(CASE_PATH)
    sim_module = load_sim_module()

    check_bundle_shape(bundle)
    check_scenario(bundle, case)
    check_controller(bundle, case)
    check_trace_and_metrics(bundle, case, sim_module)
    print("All checks passed.")


if __name__ == "__main__":
    main()
