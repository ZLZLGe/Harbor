#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


def locate_paths():
    root_config = Path("/root/quadrotor_case.json")
    root_output = Path("/root/artifacts/quadrotor_hover_linearization.json")
    try:
        if root_config.exists() and root_output.exists():
            return root_config, root_output
    except PermissionError:
        pass

    task_dir = Path(__file__).resolve().parents[1]
    return (
        task_dir / "environment" / "quadrotor_case.json",
        task_dir / "artifacts" / "quadrotor_hover_linearization.json",
    )


CONFIG_PATH, OUTPUT_PATH = locate_paths()
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
OUTPUT = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

DT = float(CONFIG["dt"])
MASS = float(CONFIG["mass"])
INERTIA = float(CONFIG["inertia"])
ARM_LENGTH = float(CONFIG["arm_length"])
GRAVITY = float(CONFIG["gravity"])


def matrix_exponential(matrix, dt):
    scaled = np.array(matrix, dtype=float) * dt
    result = np.eye(scaled.shape[0], dtype=float)
    term = np.eye(scaled.shape[0], dtype=float)
    for order in range(1, 6):
        term = term @ scaled / float(order)
        result = result + term
    return result


def hover_reference():
    reference_state = np.array(CONFIG["hover_state"], dtype=float)
    hover_thrust = 0.5 * MASS * GRAVITY
    reference_input = np.array([hover_thrust, hover_thrust], dtype=float)
    return reference_state, reference_input


def dynamics(state, control):
    _, _, theta, vx, vz, omega = np.asarray(state, dtype=float)
    u_left, u_right = np.asarray(control, dtype=float)
    total_thrust = u_left + u_right
    return np.array(
        [
            vx,
            vz,
            omega,
            -(total_thrust / MASS) * np.sin(theta),
            (total_thrust / MASS) * np.cos(theta) - GRAVITY,
            (ARM_LENGTH / INERTIA) * (u_right - u_left),
        ],
        dtype=float,
    )


def rk4_step(state, control):
    k1 = dynamics(state, control)
    k2 = dynamics(state + 0.5 * DT * k1, control)
    k3 = dynamics(state + 0.5 * DT * k2, control)
    k4 = dynamics(state + DT * k3, control)
    return state + (DT / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def continuous_jacobian(reference_state, reference_input):
    theta = float(reference_state[2])
    total_thrust = float(np.sum(reference_input))
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)

    a_matrix = np.array(
        [
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, -(total_thrust / MASS) * cos_theta, 0.0, 0.0, 0.0],
            [0.0, 0.0, -(total_thrust / MASS) * sin_theta, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        dtype=float,
    )
    b_matrix = np.array(
        [
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [-sin_theta / MASS, -sin_theta / MASS],
            [cos_theta / MASS, cos_theta / MASS],
            [-ARM_LENGTH / INERTIA, ARM_LENGTH / INERTIA],
        ],
        dtype=float,
    )
    return a_matrix, b_matrix


def discretize(a_continuous, b_continuous):
    augmented = np.zeros((8, 8), dtype=float)
    augmented[:6, :6] = a_continuous
    augmented[:6, 6:] = b_continuous
    discrete_augmented = matrix_exponential(augmented, DT)
    return discrete_augmented[:6, :6], discrete_augmented[:6, 6:]


def controllability_rank(a_discrete, b_discrete):
    blocks = [b_discrete]
    power = np.eye(a_discrete.shape[0], dtype=float)
    for _ in range(1, a_discrete.shape[0]):
        power = power @ a_discrete
        blocks.append(power @ b_discrete)
    return int(np.linalg.matrix_rank(np.hstack(blocks)))


def expected_output():
    reference_state, reference_input = hover_reference()
    steady_state_residual = dynamics(reference_state, reference_input)
    a_continuous, b_continuous = continuous_jacobian(reference_state, reference_input)
    a_discrete, b_discrete = discretize(a_continuous, b_continuous)

    validation_case = CONFIG["validation_case"]
    steps = int(validation_case["steps"])
    state_deviation = np.array(validation_case["initial_offset"], dtype=float)
    input_deviation = np.array(validation_case["input_offset"], dtype=float)
    initial_state = reference_state + state_deviation
    applied_input = reference_input + input_deviation

    nonlinear_state = initial_state.copy()
    linear_state = initial_state.copy()
    nonlinear_rollout = []
    linear_rollout = []

    for _ in range(steps):
        nonlinear_state = rk4_step(nonlinear_state, applied_input)
        delta_state = linear_state - reference_state
        linear_state = reference_state + a_discrete @ delta_state + b_discrete @ input_deviation
        nonlinear_rollout.append(nonlinear_state.copy())
        linear_rollout.append(linear_state.copy())

    nonlinear_array = np.array(nonlinear_rollout, dtype=float)
    linear_array = np.array(linear_rollout, dtype=float)
    error = nonlinear_array - linear_array

    return {
        "reference_state": reference_state,
        "reference_input": reference_input,
        "steady_state_residual": steady_state_residual,
        "continuous_A": a_continuous,
        "continuous_B": b_continuous,
        "discrete_A": a_discrete,
        "discrete_B": b_discrete,
        "controllability_rank": controllability_rank(a_discrete, b_discrete),
        "steps": steps,
        "initial_state": initial_state,
        "applied_input": applied_input,
        "state_deviation": state_deviation,
        "input_deviation": input_deviation,
        "nonlinear_rollout": nonlinear_array,
        "linear_rollout": linear_array,
        "max_position_error_norm": float(np.max(np.linalg.norm(error[:, :2], axis=1))),
        "max_velocity_error_norm": float(np.max(np.linalg.norm(error[:, 3:5], axis=1))),
        "max_attitude_error": float(np.max(np.abs(error[:, 2]))),
        "rmse_by_state": np.sqrt(np.mean(np.square(error), axis=0)),
        "final_abs_error": np.abs(error[-1]),
    }


EXPECTED = expected_output()


def assert_close(actual, expected, atol=1e-10):
    actual_array = np.array(actual, dtype=float)
    expected_array = np.array(expected, dtype=float)
    assert actual_array.shape == expected_array.shape, (actual_array.shape, expected_array.shape)
    max_error = float(np.max(np.abs(actual_array - expected_array)))
    assert max_error <= atol, f"max error {max_error} exceeds tolerance {atol}"


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_schema():
    for field in [
        "hover_equilibrium",
        "continuous_model",
        "discrete_model",
        "validation",
        "acceptance",
    ]:
        assert field in OUTPUT, f"missing top-level field {field}"

    assert OUTPUT["continuous_model"]["state_order"] == ["x", "z", "theta", "vx", "vz", "omega"]
    assert OUTPUT["continuous_model"]["input_order"] == ["u_left", "u_right"]
    assert OUTPUT["discrete_model"]["method"] == "zoh"


def test_models_and_equilibrium():
    equilibrium = OUTPUT["hover_equilibrium"]
    assert_close(equilibrium["reference_state"], EXPECTED["reference_state"])
    assert_close(equilibrium["reference_input"], EXPECTED["reference_input"])
    assert_close(equilibrium["steady_state_residual"], EXPECTED["steady_state_residual"], atol=1e-12)

    assert_close(OUTPUT["continuous_model"]["A"], EXPECTED["continuous_A"])
    assert_close(OUTPUT["continuous_model"]["B"], EXPECTED["continuous_B"])
    assert_close(OUTPUT["discrete_model"]["A"], EXPECTED["discrete_A"])
    assert_close(OUTPUT["discrete_model"]["B"], EXPECTED["discrete_B"])
    assert OUTPUT["discrete_model"]["controllability_rank"] == EXPECTED["controllability_rank"]


def test_validation_and_thresholds():
    validation = OUTPUT["validation"]
    assert validation["steps"] == EXPECTED["steps"]
    assert_close(validation["initial_state"], EXPECTED["initial_state"])
    assert_close(validation["applied_input"], EXPECTED["applied_input"])
    assert_close(validation["state_deviation"], EXPECTED["state_deviation"])
    assert_close(validation["input_deviation"], EXPECTED["input_deviation"])
    assert_close(validation["nonlinear_rollout"], EXPECTED["nonlinear_rollout"])
    assert_close(validation["linear_rollout"], EXPECTED["linear_rollout"])
    assert_close([validation["max_position_error_norm"]], [EXPECTED["max_position_error_norm"]])
    assert_close([validation["max_velocity_error_norm"]], [EXPECTED["max_velocity_error_norm"]])
    assert_close([validation["max_attitude_error"]], [EXPECTED["max_attitude_error"]], atol=1e-12)
    assert_close(validation["rmse_by_state"], EXPECTED["rmse_by_state"])
    assert_close(validation["final_abs_error"], EXPECTED["final_abs_error"])

    thresholds = CONFIG["quality_thresholds"]
    assert validation["max_position_error_norm"] <= thresholds["max_position_error_norm"]
    assert validation["max_velocity_error_norm"] <= thresholds["max_velocity_error_norm"]
    assert validation["max_attitude_error"] <= thresholds["max_attitude_error"]


def test_acceptance_summary():
    acceptance = OUTPUT["acceptance"]
    assert acceptance["within_threshold"] is True
    assert abs(acceptance["thresholds"]["max_position_error_norm"] - CONFIG["quality_thresholds"]["max_position_error_norm"]) <= 1e-12
    assert abs(acceptance["thresholds"]["max_velocity_error_norm"] - CONFIG["quality_thresholds"]["max_velocity_error_norm"]) <= 1e-12
    assert abs(acceptance["thresholds"]["max_attitude_error"] - CONFIG["quality_thresholds"]["max_attitude_error"]) <= 1e-12
    assert isinstance(acceptance["summary"], str) and "悬停" in acceptance["summary"] and acceptance["summary"].strip()


def main():
    test_output_exists()
    test_schema()
    test_models_and_equilibrium()
    test_validation_and_thresholds()
    test_acceptance_summary()
    print("All checks passed.")


if __name__ == "__main__":
    main()
