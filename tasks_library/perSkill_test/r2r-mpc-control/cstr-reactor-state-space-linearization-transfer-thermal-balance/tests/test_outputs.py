#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


def locate_paths():
    root_config = Path("/root/cstr_case.json")
    root_output = Path("/root/artifacts/cstr_operating_point_linearization.json")
    try:
        if root_config.exists() and root_output.exists():
            return root_config, root_output
    except PermissionError:
        pass

    task_dir = Path(__file__).resolve().parents[1]
    return (
        task_dir / "environment" / "cstr_case.json",
        task_dir / "artifacts" / "cstr_operating_point_linearization.json",
    )


CONFIG_PATH, OUTPUT_PATH = locate_paths()
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
OUTPUT = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

DT = float(CONFIG["dt"])
CA_F = float(CONFIG["feed_concentration"])
TAU = float(CONFIG["residence_time"])
K0 = float(CONFIG["k0"])
E_OVER_R = float(CONFIG["E_over_R"])
T_F = float(CONFIG["feed_temperature"])
T_C = float(CONFIG["coolant_inlet_temperature"])
HEAT_RELEASE_GAIN = float(CONFIG["heat_release_gain"])
COOLING_GAIN = float(CONFIG["cooling_gain"])


def matrix_exponential(matrix):
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    exp_diag = np.diag(np.exp(eigenvalues))
    result = eigenvectors @ exp_diag @ np.linalg.inv(eigenvectors)
    return np.real_if_close(result, tol=1000).astype(float)


def reaction_rate(state):
    concentration, temperature = state
    return K0 * np.exp(-E_OVER_R / temperature) * concentration


def dynamics(state, control):
    concentration, temperature = state
    coolant_flow = float(control[0])
    rate = reaction_rate(state)
    return np.array(
        [
            (CA_F - concentration) / TAU - rate,
            (T_F - temperature) / TAU
            + HEAT_RELEASE_GAIN * rate
            - COOLING_GAIN * coolant_flow * (temperature - T_C),
        ],
        dtype=float,
    )


def rk4_step(state, control):
    k1 = dynamics(state, control)
    k2 = dynamics(state + 0.5 * DT * k1, control)
    k3 = dynamics(state + 0.5 * DT * k2, control)
    k4 = dynamics(state + DT * k3, control)
    return state + (DT / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def operating_point():
    concentration = CA_F * (1.0 - float(CONFIG["target_conversion"]))
    temperature = float(CONFIG["nominal_temperature"])
    state = np.array([concentration, temperature], dtype=float)
    rate = reaction_rate(state)
    control = np.array(
        [
            ((T_F - temperature) / TAU + HEAT_RELEASE_GAIN * rate)
            / (COOLING_GAIN * (temperature - T_C))
        ],
        dtype=float,
    )
    return state, control


def continuous_jacobian(state, control):
    concentration, temperature = state
    coolant_flow = float(control[0])
    exp_term = np.exp(-E_OVER_R / temperature)
    rate_gain = K0 * exp_term
    temperature_sensitivity = rate_gain * concentration * (E_OVER_R / (temperature ** 2))

    a_matrix = np.array(
        [
            [-1.0 / TAU - rate_gain, -temperature_sensitivity],
            [HEAT_RELEASE_GAIN * rate_gain, -1.0 / TAU + HEAT_RELEASE_GAIN * temperature_sensitivity - COOLING_GAIN * coolant_flow],
        ],
        dtype=float,
    )
    b_matrix = np.array([[0.0], [-COOLING_GAIN * (temperature - T_C)]], dtype=float)
    return a_matrix, b_matrix


def expected_output():
    reference_state, reference_input = operating_point()
    steady_state_residual = dynamics(reference_state, reference_input)
    a_continuous, b_continuous = continuous_jacobian(reference_state, reference_input)

    augmented = np.zeros((3, 3), dtype=float)
    augmented[:2, :2] = a_continuous
    augmented[:2, 2:] = b_continuous
    discrete_augmented = matrix_exponential(augmented * DT)
    a_discrete = discrete_augmented[:2, :2]
    b_discrete = discrete_augmented[:2, 2:]
    eigenvalues = np.linalg.eigvals(a_discrete)

    validation_case = CONFIG["validation_case"]
    steps = int(validation_case["steps"])
    initial_offset = np.array(validation_case["initial_offset"], dtype=float)
    input_offset = np.array(validation_case["input_offset"], dtype=float)
    initial_state = reference_state + initial_offset
    applied_input = reference_input + input_offset

    nonlinear_state = initial_state.copy()
    linear_state = initial_state.copy()
    nonlinear_rollout = []
    linear_rollout = []

    for _ in range(steps):
        nonlinear_state = rk4_step(nonlinear_state, applied_input)
        delta_state = linear_state - reference_state
        linear_state = reference_state + a_discrete @ delta_state + (b_discrete @ input_offset).ravel()
        nonlinear_rollout.append(nonlinear_state.copy())
        linear_rollout.append(linear_state.copy())

    nonlinear_array = np.array(nonlinear_rollout, dtype=float)
    linear_array = np.array(linear_rollout, dtype=float)
    abs_error = np.abs(nonlinear_array - linear_array)
    rmse_by_state = np.sqrt(np.mean(np.square(nonlinear_array - linear_array), axis=0))

    return {
        "reference_state": reference_state,
        "reference_input": reference_input,
        "steady_state_residual": steady_state_residual,
        "continuous_A": a_continuous,
        "continuous_B": b_continuous,
        "discrete_A": a_discrete,
        "discrete_B": b_discrete,
        "eigenvalues": eigenvalues,
        "steps": steps,
        "initial_state": initial_state,
        "applied_input": applied_input,
        "input_offset": input_offset,
        "nonlinear_rollout": nonlinear_array,
        "linear_rollout": linear_array,
        "max_abs_error": float(np.max(abs_error)),
        "rmse_by_state": rmse_by_state,
        "final_abs_error": abs_error[-1],
    }


EXPECTED = expected_output()


def assert_close(actual, expected, atol=1e-9):
    actual_array = np.array(actual, dtype=float)
    expected_array = np.array(expected, dtype=float)
    assert actual_array.shape == expected_array.shape, (actual_array.shape, expected_array.shape)
    max_error = float(np.max(np.abs(actual_array - expected_array)))
    assert max_error <= atol, f"max error {max_error} exceeds tolerance {atol}"


def test_schema():
    for field in [
        "operating_point",
        "continuous_model",
        "discrete_model",
        "validation",
        "quality_summary",
    ]:
        assert field in OUTPUT, f"missing top-level field {field}"

    assert OUTPUT["continuous_model"]["state_order"] == ["C_A", "T"]
    assert OUTPUT["continuous_model"]["input_order"] == ["q_c"]
    assert OUTPUT["discrete_model"]["method"] == "zoh"
    assert len(OUTPUT["discrete_model"]["eigenvalues"]) == 2


def test_operating_point_and_models():
    operating_point_output = OUTPUT["operating_point"]
    assert abs(operating_point_output["target_conversion"] - CONFIG["target_conversion"]) <= 1e-12
    assert_close(operating_point_output["reference_state"], EXPECTED["reference_state"])
    assert_close(operating_point_output["reference_input"], EXPECTED["reference_input"])
    assert_close(operating_point_output["steady_state_residual"], EXPECTED["steady_state_residual"], atol=1e-12)

    assert_close(OUTPUT["continuous_model"]["A"], EXPECTED["continuous_A"])
    assert_close(OUTPUT["continuous_model"]["B"], EXPECTED["continuous_B"])
    assert_close(OUTPUT["discrete_model"]["A"], EXPECTED["discrete_A"])
    assert_close(OUTPUT["discrete_model"]["B"], EXPECTED["discrete_B"])

    actual_eigs = [
        complex(item["real"], item["imag"])
        for item in OUTPUT["discrete_model"]["eigenvalues"]
    ]
    expected_eigs = EXPECTED["eigenvalues"]
    actual_sorted = sorted(actual_eigs, key=lambda value: (round(value.real, 12), round(value.imag, 12)))
    expected_sorted = sorted(expected_eigs, key=lambda value: (round(value.real, 12), round(value.imag, 12)))
    assert_close(
        [[value.real, value.imag] for value in actual_sorted],
        [[value.real, value.imag] for value in expected_sorted],
    )


def test_validation_rollout_and_metrics():
    validation_output = OUTPUT["validation"]
    assert validation_output["steps"] == EXPECTED["steps"]
    assert_close(validation_output["initial_state"], EXPECTED["initial_state"])
    assert_close(validation_output["applied_input"], EXPECTED["applied_input"])
    assert_close(validation_output["input_deviation"], EXPECTED["input_offset"])
    assert_close(validation_output["nonlinear_rollout"], EXPECTED["nonlinear_rollout"])
    assert_close(validation_output["linear_rollout"], EXPECTED["linear_rollout"])
    assert_close([validation_output["max_abs_error"]], [EXPECTED["max_abs_error"]])
    assert_close(validation_output["rmse_by_state"], EXPECTED["rmse_by_state"])
    assert_close(validation_output["final_abs_error"], EXPECTED["final_abs_error"])

    thresholds = CONFIG["quality_thresholds"]
    assert validation_output["max_abs_error"] <= thresholds["max_abs_error"]
    assert validation_output["rmse_by_state"][1] <= thresholds["temperature_rmse"]


def test_quality_summary():
    summary = OUTPUT["quality_summary"]
    assert summary["short_horizon_match"] is True
    assert abs(summary["thresholds"]["max_abs_error"] - CONFIG["quality_thresholds"]["max_abs_error"]) <= 1e-12
    assert abs(summary["thresholds"]["temperature_rmse"] - CONFIG["quality_thresholds"]["temperature_rmse"]) <= 1e-12
    assert isinstance(summary["summary"], str) and "短时" in summary["summary"] and summary["summary"].strip()


def main():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    test_schema()
    test_operating_point_and_models()
    test_validation_rollout_and_metrics()
    test_quality_summary()
    print("All checks passed.")


if __name__ == "__main__":
    main()
