#!/usr/bin/env python3

import csv
import json
from pathlib import Path

import numpy as np


def locate_paths():
    root_config = Path("/root/microgrid_case.json")
    root_schedule = Path("/root/load_step_profile.csv")
    root_output = Path("/root/artifacts/microgrid_droop_linearization.json")
    try:
        if root_config.exists() and root_schedule.exists() and root_output.exists():
            return root_config, root_schedule, root_output
    except PermissionError:
        pass

    task_dir = Path(__file__).resolve().parents[1]
    return (
        task_dir / "environment" / "microgrid_case.json",
        task_dir / "environment" / "load_step_profile.csv",
        task_dir / "artifacts" / "microgrid_droop_linearization.json",
    )


CONFIG_PATH, SCHEDULE_PATH, OUTPUT_PATH = locate_paths()
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
OUTPUT = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def load_schedule(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "time_s": float(row["time_s"]),
                "loads": np.array(
                    [float(row["active_load_pu"]), float(row["reactive_load_pu"])],
                    dtype=float,
                ),
            }
            for row in reader
        ]


SCHEDULE = load_schedule(SCHEDULE_PATH)
DT = float(CONFIG["dt"])
REFERENCE_STATE = np.array(CONFIG["nominal_operating_point"]["reference_state"], dtype=float)
REFERENCE_INPUT = np.array(CONFIG["nominal_operating_point"]["reference_input"], dtype=float)
PARAMS = CONFIG["model_parameters"]
TOLERANCES = CONFIG["error_tolerances"]


def dynamics(state, control):
    delta_f_hz, delta_v_pu = np.asarray(state, dtype=float)
    active_load_pu, reactive_load_pu = np.asarray(control, dtype=float)
    voltage_ratio = (PARAMS["nominal_voltage_pu"] + delta_v_pu) / PARAMS["nominal_voltage_pu"]
    active_term = (
        active_load_pu
        * voltage_ratio ** PARAMS["active_voltage_exponent"]
        * (1.0 + PARAMS["active_frequency_coupling"] * delta_f_hz)
    )
    reactive_term = (
        reactive_load_pu
        * voltage_ratio ** PARAMS["reactive_voltage_exponent"]
        * (1.0 + PARAMS["reactive_frequency_coupling"] * delta_f_hz)
    )
    return np.array(
        [
            (
                -delta_f_hz
                - PARAMS["active_droop_gain"] * (active_term - REFERENCE_INPUT[0])
            )
            / PARAMS["tau_frequency"],
            (
                -delta_v_pu
                - PARAMS["reactive_droop_gain"] * (reactive_term - REFERENCE_INPUT[1])
            )
            / PARAMS["tau_voltage"],
        ],
        dtype=float,
    )


def rk4_step(state, control):
    k1 = dynamics(state, control)
    k2 = dynamics(state + 0.5 * DT * k1, control)
    k3 = dynamics(state + 0.5 * DT * k2, control)
    k4 = dynamics(state + DT * k3, control)
    return state + (DT / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def continuous_jacobian():
    active_nominal = float(REFERENCE_INPUT[0])
    reactive_nominal = float(REFERENCE_INPUT[1])
    nominal_voltage = float(PARAMS["nominal_voltage_pu"])
    return (
        np.array(
            [
                [
                    (
                        -1.0
                        - PARAMS["active_droop_gain"]
                        * active_nominal
                        * PARAMS["active_frequency_coupling"]
                    )
                    / PARAMS["tau_frequency"],
                    (
                        -PARAMS["active_droop_gain"]
                        * active_nominal
                        * PARAMS["active_voltage_exponent"]
                        / nominal_voltage
                    )
                    / PARAMS["tau_frequency"],
                ],
                [
                    (
                        -PARAMS["reactive_droop_gain"]
                        * reactive_nominal
                        * PARAMS["reactive_frequency_coupling"]
                    )
                    / PARAMS["tau_voltage"],
                    (
                        -1.0
                        - PARAMS["reactive_droop_gain"]
                        * reactive_nominal
                        * PARAMS["reactive_voltage_exponent"]
                        / nominal_voltage
                    )
                    / PARAMS["tau_voltage"],
                ],
            ],
            dtype=float,
        ),
        np.array(
            [
                [-PARAMS["active_droop_gain"] / PARAMS["tau_frequency"], 0.0],
                [0.0, -PARAMS["reactive_droop_gain"] / PARAMS["tau_voltage"]],
            ],
            dtype=float,
        ),
    )


def matrix_exponential(matrix):
    eigenvalues, eigenvectors = np.linalg.eig(np.asarray(matrix, dtype=float))
    exp_diag = np.diag(np.exp(eigenvalues))
    result = eigenvectors @ exp_diag @ np.linalg.inv(eigenvectors)
    return np.real_if_close(result, tol=1000).astype(float)


def zoh_discretize(a_matrix, b_matrix):
    augmented = np.zeros((4, 4), dtype=float)
    augmented[:2, :2] = a_matrix
    augmented[:2, 2:] = b_matrix
    discrete_augmented = matrix_exponential(augmented * DT)
    return discrete_augmented[:2, :2], discrete_augmented[:2, 2:]


def sorted_eigenvalue_pairs(values):
    pairs = [
        {"real": float(np.real(value)), "imag": float(np.imag(value))}
        for value in values
    ]
    pairs.sort(key=lambda item: (round(item["real"], 12), round(item["imag"], 12)))
    return pairs


def scheduled_load(time_s):
    active = SCHEDULE[0]["loads"]
    for point in SCHEDULE:
        if time_s >= point["time_s"]:
            active = point["loads"]
        else:
            break
    return active.copy()


def state_trace(entries):
    return np.array(
        [[entry["frequency_deviation_hz"], entry["voltage_deviation_pu"]] for entry in entries],
        dtype=float,
    )


def expected_output():
    a_continuous, b_continuous = continuous_jacobian()
    a_discrete, b_discrete = zoh_discretize(a_continuous, b_continuous)
    steps = int(CONFIG["validation_case"]["steps"])
    initial_state = np.array(CONFIG["validation_case"]["initial_state"], dtype=float)

    nonlinear_state = initial_state.copy()
    linear_state = initial_state.copy()
    applied_load_sequence = []
    nonlinear_rollout = []
    linear_rollout = []

    for step_idx in range(steps):
        time_s = step_idx * DT
        load = scheduled_load(time_s)
        nonlinear_state = rk4_step(nonlinear_state, load)
        linear_state = a_discrete @ linear_state + b_discrete @ (load - REFERENCE_INPUT)

        applied_load_sequence.append({"time": float(time_s), "loads": load.tolist()})
        nonlinear_rollout.append(
            {
                "time": float((step_idx + 1) * DT),
                "frequency_deviation_hz": float(nonlinear_state[0]),
                "voltage_deviation_pu": float(nonlinear_state[1]),
            }
        )
        linear_rollout.append(
            {
                "time": float((step_idx + 1) * DT),
                "frequency_deviation_hz": float(linear_state[0]),
                "voltage_deviation_pu": float(linear_state[1]),
            }
        )

    nonlinear_array = state_trace(nonlinear_rollout)
    linear_array = state_trace(linear_rollout)
    gap = np.abs(nonlinear_array - linear_array)

    return {
        "steady_state_residual": dynamics(REFERENCE_STATE, REFERENCE_INPUT),
        "continuous_A": a_continuous,
        "continuous_B": b_continuous,
        "discrete_A": a_discrete,
        "discrete_B": b_discrete,
        "eigenvalues": sorted_eigenvalue_pairs(np.linalg.eigvals(a_discrete)),
        "steps": steps,
        "initial_state": initial_state,
        "applied_load_sequence": applied_load_sequence,
        "nonlinear_rollout": nonlinear_rollout,
        "linear_rollout": linear_rollout,
        "max_abs_frequency_gap_hz": float(np.max(gap[:, 0])),
        "max_abs_voltage_gap_pu": float(np.max(gap[:, 1])),
        "frequency_nadir_gap_hz": float(
            abs(np.min(nonlinear_array[:, 0]) - np.min(linear_array[:, 0]))
        ),
        "voltage_nadir_gap_pu": float(
            abs(np.min(nonlinear_array[:, 1]) - np.min(linear_array[:, 1]))
        ),
        "final_state_gap": gap[-1],
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
        "nominal_operating_point",
        "continuous_small_signal_model",
        "discrete_small_signal_model",
        "load_step_validation",
        "assessment",
    ]:
        assert field in OUTPUT, f"missing top-level field {field}"

    nominal = OUTPUT["nominal_operating_point"]
    assert nominal["state_order"] == ["delta_f_hz", "delta_v_pu"]
    assert nominal["input_order"] == ["P_load_pu", "Q_load_pu"]
    assert OUTPUT["discrete_small_signal_model"]["method"] == "zoh"


def test_models():
    nominal = OUTPUT["nominal_operating_point"]
    assert_close(nominal["reference_state"], REFERENCE_STATE)
    assert_close(nominal["reference_input"], REFERENCE_INPUT)
    assert_close(nominal["steady_state_residual"], EXPECTED["steady_state_residual"], atol=1e-12)

    assert_close(OUTPUT["continuous_small_signal_model"]["A"], EXPECTED["continuous_A"])
    assert_close(OUTPUT["continuous_small_signal_model"]["B"], EXPECTED["continuous_B"])
    assert_close(OUTPUT["discrete_small_signal_model"]["A"], EXPECTED["discrete_A"])
    assert_close(OUTPUT["discrete_small_signal_model"]["B"], EXPECTED["discrete_B"])
    assert OUTPUT["discrete_small_signal_model"]["eigenvalues"] == EXPECTED["eigenvalues"]


def test_load_step_validation():
    validation = OUTPUT["load_step_validation"]
    assert validation["steps"] == EXPECTED["steps"]
    assert_close(validation["initial_state"], EXPECTED["initial_state"], atol=1e-12)

    assert validation["applied_load_sequence"] == EXPECTED["applied_load_sequence"]
    assert validation["nonlinear_rollout"] == EXPECTED["nonlinear_rollout"]
    assert validation["linear_rollout"] == EXPECTED["linear_rollout"]

    assert_close(
        [validation["max_abs_frequency_gap_hz"]],
        [EXPECTED["max_abs_frequency_gap_hz"]],
        atol=1e-12,
    )
    assert_close(
        [validation["max_abs_voltage_gap_pu"]],
        [EXPECTED["max_abs_voltage_gap_pu"]],
        atol=1e-12,
    )
    assert_close(
        [validation["frequency_nadir_gap_hz"]],
        [EXPECTED["frequency_nadir_gap_hz"]],
        atol=1e-12,
    )
    assert_close(
        [validation["voltage_nadir_gap_pu"]],
        [EXPECTED["voltage_nadir_gap_pu"]],
        atol=1e-12,
    )
    assert_close(validation["final_state_gap"], EXPECTED["final_state_gap"], atol=1e-12)


def test_thresholds_and_summary():
    validation = OUTPUT["load_step_validation"]
    assert validation["max_abs_frequency_gap_hz"] <= TOLERANCES["max_abs_frequency_gap_hz"]
    assert validation["max_abs_voltage_gap_pu"] <= TOLERANCES["max_abs_voltage_gap_pu"]
    assert validation["frequency_nadir_gap_hz"] <= TOLERANCES["frequency_nadir_gap_hz"]
    assert validation["voltage_nadir_gap_pu"] <= TOLERANCES["voltage_nadir_gap_pu"]

    assessment = OUTPUT["assessment"]
    assert assessment["within_tolerance"] is True
    assert assessment["thresholds"] == TOLERANCES
    assert isinstance(assessment["summary"], str) and assessment["summary"].strip()
    assert "频率" in assessment["summary"]
    assert "电压" in assessment["summary"]
    assert "负载" in assessment["summary"]


def main():
    test_output_exists()
    test_schema()
    test_models()
    test_load_step_validation()
    test_thresholds_and_summary()
    print("All checks passed.")


if __name__ == "__main__":
    main()
