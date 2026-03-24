#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


def locate_paths():
    root_config = Path("/root/dual_regime_config.json")
    root_output = Path("/root/artifacts/r2r_dual_regime_linearization.json")
    try:
        if root_config.exists() and root_output.exists():
            return (root_config, root_output)
    except PermissionError:
        pass

    task_dir = Path(__file__).resolve().parents[1]
    return (
        task_dir / "environment" / "dual_regime_config.json",
        task_dir / "artifacts" / "r2r_dual_regime_linearization.json",
    )


CONFIG_PATH, OUTPUT_PATH = locate_paths()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


CONFIG = load_json(CONFIG_PATH)
OUTPUT = load_json(OUTPUT_PATH)

DT = CONFIG["dt"]
EA = CONFIG["EA"]
J = CONFIG["J"]
R = CONFIG["R"]
FB = CONFIG["fb"]
L = CONFIG["L"]
V0 = CONFIG["v0"]
NUM_SEC = CONFIG["num_sections"]


def steady_state_velocities(reference_tensions):
    v_ref = np.zeros(NUM_SEC)
    v_prev = V0
    tension_prev = 0.0
    for idx in range(NUM_SEC):
        v_ref[idx] = (EA - tension_prev) / (EA - reference_tensions[idx]) * v_prev
        v_prev = v_ref[idx]
        tension_prev = reference_tensions[idx]
    return v_ref


def steady_state_input(x_ref):
    u_ref = np.zeros(NUM_SEC)
    for idx in range(NUM_SEC):
        tension_next = x_ref[idx + 1] if idx < NUM_SEC - 1 else 0.0
        u_ref[idx] = FB / R * x_ref[NUM_SEC + idx] - R * (tension_next - x_ref[idx])
    return u_ref


def continuous_jacobian(x_ref):
    a_mat = np.zeros((2 * NUM_SEC, 2 * NUM_SEC))
    b_mat = np.zeros((2 * NUM_SEC, NUM_SEC))

    for idx in range(NUM_SEC):
        velocity = x_ref[NUM_SEC + idx]
        tension = x_ref[idx]

        a_mat[idx, idx] = -velocity / L
        a_mat[idx, NUM_SEC + idx] = EA / L - tension / L
        if idx > 0:
            velocity_prev = x_ref[NUM_SEC + idx - 1]
            tension_prev = x_ref[idx - 1]
            a_mat[idx, idx - 1] = velocity_prev / L
            a_mat[idx, NUM_SEC + idx - 1] = -EA / L + tension_prev / L

        a_mat[NUM_SEC + idx, idx] = -(R ** 2) / J
        a_mat[NUM_SEC + idx, NUM_SEC + idx] = -FB / J
        if idx < NUM_SEC - 1:
            a_mat[NUM_SEC + idx, idx + 1] = (R ** 2) / J
        b_mat[NUM_SEC + idx, idx] = R / J

    return a_mat, b_mat


def discretize(a_continuous, b_continuous):
    return np.eye(2 * NUM_SEC) + DT * a_continuous, DT * b_continuous


def nonlinear_step(x_state, u_input, inlet_velocity):
    tensions = x_state[:NUM_SEC]
    velocities = x_state[NUM_SEC:]

    velocity_prev = np.concatenate([[inlet_velocity], velocities[:-1]])
    tension_prev = np.concatenate([[0.0], tensions[:-1]])
    tension_rate = (EA / L) * (velocities - velocity_prev) + (
        velocity_prev * tension_prev - velocities * tensions
    ) / L

    tension_next = np.concatenate([tensions[1:], [0.0]])
    velocity_rate = ((R ** 2) / J) * (tension_next - tensions) + (R / J) * u_input - (FB / J) * velocities

    next_tensions = np.maximum(tensions + DT * tension_rate, 0.0)
    next_velocities = velocities + DT * velocity_rate
    return np.concatenate([next_tensions, next_velocities])


def expected_regime(regime_name):
    reference_tensions = np.array(
        CONFIG["operating_points"][regime_name]["reference_tensions"], dtype=float
    )
    reference_velocities = steady_state_velocities(reference_tensions)
    reference_state = np.concatenate([reference_tensions, reference_velocities])
    reference_input = steady_state_input(reference_state)
    a_continuous, b_continuous = continuous_jacobian(reference_state)
    a_discrete, b_discrete = discretize(a_continuous, b_continuous)

    case = CONFIG["validation_cases"][regime_name]
    state_offset = np.array(case["state_offset"], dtype=float)
    control_offset = np.array(case["control_offset"], dtype=float)
    steps = int(case["steps"])
    initial_state = reference_state + state_offset
    control_input = reference_input + control_offset
    inlet_velocity = reference_state[NUM_SEC]

    nonlinear_state = initial_state.copy()
    linear_state = initial_state.copy()
    nonlinear_rollout = []
    linear_rollout = []

    for _ in range(steps):
        nonlinear_state = nonlinear_step(nonlinear_state, control_input, inlet_velocity)
        delta_state = linear_state - reference_state
        linear_state = reference_state + a_discrete @ delta_state + b_discrete @ control_offset
        nonlinear_rollout.append(nonlinear_state.copy())
        linear_rollout.append(linear_state.copy())

    nonlinear_array = np.array(nonlinear_rollout)
    linear_array = np.array(linear_rollout)
    error = np.abs(nonlinear_array - linear_array)

    return {
        "reference_state": reference_state,
        "reference_input": reference_input,
        "continuous_A": a_continuous,
        "continuous_B": b_continuous,
        "discrete_A": a_discrete,
        "discrete_B": b_discrete,
        "steps": steps,
        "initial_state": initial_state,
        "control_input": control_input,
        "nonlinear_rollout": nonlinear_array,
        "linear_rollout": linear_array,
        "max_abs_state_error": float(np.max(error)),
        "mean_abs_tension_error": float(np.mean(error[:, :NUM_SEC])),
        "mean_abs_velocity_error": float(np.mean(error[:, NUM_SEC:])),
    }


def assert_close(actual, expected, atol=1e-8):
    actual_array = np.array(actual, dtype=float)
    expected_array = np.array(expected, dtype=float)
    assert actual_array.shape == expected_array.shape
    max_error = np.max(np.abs(actual_array - expected_array))
    assert max_error <= atol, f"max error {max_error} exceeds tolerance {atol}"


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_top_level_schema():
    assert OUTPUT["dt"] == CONFIG["dt"]
    assert set(OUTPUT["regimes"].keys()) == {"pre_change", "post_change"}
    comparison = OUTPUT["comparison"]
    for field in [
        "max_abs_continuous_A_delta",
        "max_abs_continuous_B_delta",
        "max_abs_discrete_A_delta",
        "max_abs_discrete_B_delta",
        "validation_passed",
        "summary",
    ]:
        assert field in comparison, f"missing comparison field {field}"
    assert isinstance(comparison["summary"], str) and comparison["summary"].strip()


def test_regime_models_and_rollouts():
    for regime_name in ["pre_change", "post_change"]:
        submitted = OUTPUT["regimes"][regime_name]
        expected = expected_regime(regime_name)

        assert_close(submitted["reference_state"], expected["reference_state"])
        assert_close(submitted["reference_input"], expected["reference_input"])
        assert_close(submitted["continuous_model"]["A"], expected["continuous_A"])
        assert_close(submitted["continuous_model"]["B"], expected["continuous_B"])
        assert_close(submitted["discrete_model"]["A"], expected["discrete_A"])
        assert_close(submitted["discrete_model"]["B"], expected["discrete_B"])

        validation = submitted["validation"]
        assert validation["steps"] == expected["steps"]
        assert_close(validation["initial_state"], expected["initial_state"])
        assert_close(validation["control_input"], expected["control_input"])
        assert_close(validation["nonlinear_rollout"], expected["nonlinear_rollout"])
        assert_close(validation["linear_rollout"], expected["linear_rollout"])

        assert abs(validation["max_abs_state_error"] - expected["max_abs_state_error"]) <= 1e-10
        assert abs(validation["mean_abs_tension_error"] - expected["mean_abs_tension_error"]) <= 1e-10
        assert abs(validation["mean_abs_velocity_error"] - expected["mean_abs_velocity_error"]) <= 1e-12


def test_validation_thresholds_and_comparison():
    thresholds = CONFIG["error_thresholds"]
    expected_pre = expected_regime("pre_change")
    expected_post = expected_regime("post_change")

    for expected in [expected_pre, expected_post]:
        assert expected["max_abs_state_error"] <= thresholds["max_abs_state_error"]
        assert expected["mean_abs_tension_error"] <= thresholds["mean_abs_tension_error"]
        assert expected["mean_abs_velocity_error"] <= thresholds["mean_abs_velocity_error"]

    comparison = OUTPUT["comparison"]
    continuous_a_delta = np.max(
        np.abs(expected_pre["continuous_A"] - expected_post["continuous_A"])
    )
    continuous_b_delta = np.max(
        np.abs(expected_pre["continuous_B"] - expected_post["continuous_B"])
    )
    discrete_a_delta = np.max(
        np.abs(expected_pre["discrete_A"] - expected_post["discrete_A"])
    )
    discrete_b_delta = np.max(
        np.abs(expected_pre["discrete_B"] - expected_post["discrete_B"])
    )

    assert abs(comparison["max_abs_continuous_A_delta"] - float(continuous_a_delta)) <= 1e-10
    assert abs(comparison["max_abs_continuous_B_delta"] - float(continuous_b_delta)) <= 1e-10
    assert abs(comparison["max_abs_discrete_A_delta"] - float(discrete_a_delta)) <= 1e-10
    assert abs(comparison["max_abs_discrete_B_delta"] - float(discrete_b_delta)) <= 1e-12
    assert comparison["validation_passed"] is True


def main():
    tests = [
        test_output_file_exists,
        test_top_level_schema,
        test_regime_models_and_rollouts,
        test_validation_thresholds_and_comparison,
    ]
    for test in tests:
        test()
    print("All checks passed.")


if __name__ == "__main__":
    main()
