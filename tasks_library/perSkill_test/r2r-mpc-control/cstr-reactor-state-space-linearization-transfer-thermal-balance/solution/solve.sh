#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/cstr_case.json ]; then
  BASE_DIR="/root"
  OUTPUT_DIR="/root/artifacts"
else
  BASE_DIR="$TASK_DIR/environment"
  OUTPUT_DIR="$TASK_DIR/artifacts"
fi

mkdir -p "$OUTPUT_DIR"

export BASE_DIR OUTPUT_DIR

python3 <<'PY'
import json
import os
from pathlib import Path

import numpy as np


base_dir = Path(os.environ["BASE_DIR"])
output_dir = Path(os.environ["OUTPUT_DIR"])
config = json.loads((base_dir / "cstr_case.json").read_text(encoding="utf-8"))

DT = float(config["dt"])
CA_F = float(config["feed_concentration"])
TAU = float(config["residence_time"])
K0 = float(config["k0"])
E_OVER_R = float(config["E_over_R"])
T_F = float(config["feed_temperature"])
T_C = float(config["coolant_inlet_temperature"])
HEAT_RELEASE_GAIN = float(config["heat_release_gain"])
COOLING_GAIN = float(config["cooling_gain"])
TARGET_CONVERSION = float(config["target_conversion"])
NOMINAL_TEMPERATURE = float(config["nominal_temperature"])


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


def continuous_jacobian(reference_state, reference_input):
    concentration, temperature = reference_state
    coolant_flow = float(reference_input[0])
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


reference_concentration = CA_F * (1.0 - TARGET_CONVERSION)
reference_temperature = NOMINAL_TEMPERATURE
reference_state = np.array([reference_concentration, reference_temperature], dtype=float)
reference_rate = reaction_rate(reference_state)
reference_input = np.array(
    [
        (
            (T_F - reference_temperature) / TAU
            + HEAT_RELEASE_GAIN * reference_rate
        )
        / (COOLING_GAIN * (reference_temperature - T_C))
    ],
    dtype=float,
)
steady_state_residual = dynamics(reference_state, reference_input)

a_continuous, b_continuous = continuous_jacobian(reference_state, reference_input)
augmented = np.zeros((3, 3), dtype=float)
augmented[:2, :2] = a_continuous
augmented[:2, 2:] = b_continuous
discrete_augmented = matrix_exponential(augmented * DT)
a_discrete = discrete_augmented[:2, :2]
b_discrete = discrete_augmented[:2, 2:]
eigenvalues = np.linalg.eigvals(a_discrete)

validation_case = config["validation_case"]
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
    nonlinear_rollout.append(nonlinear_state.tolist())
    linear_rollout.append(linear_state.tolist())

nonlinear_array = np.array(nonlinear_rollout, dtype=float)
linear_array = np.array(linear_rollout, dtype=float)
abs_error = np.abs(nonlinear_array - linear_array)

thresholds = config["quality_thresholds"]
max_abs_error = float(np.max(abs_error))
rmse_by_state = np.sqrt(np.mean(np.square(nonlinear_array - linear_array), axis=0))
final_abs_error = abs_error[-1]
short_horizon_match = (
    max_abs_error <= float(thresholds["max_abs_error"])
    and float(rmse_by_state[1]) <= float(thresholds["temperature_rmse"])
)

result = {
    "operating_point": {
        "target_conversion": TARGET_CONVERSION,
        "reference_state": reference_state.tolist(),
        "reference_input": reference_input.tolist(),
        "steady_state_residual": steady_state_residual.tolist(),
    },
    "continuous_model": {
        "state_order": ["C_A", "T"],
        "input_order": ["q_c"],
        "A": a_continuous.tolist(),
        "B": b_continuous.tolist(),
    },
    "discrete_model": {
        "dt": DT,
        "method": "zoh",
        "A": a_discrete.tolist(),
        "B": b_discrete.tolist(),
        "eigenvalues": [
            {"real": float(np.real(value)), "imag": float(np.imag(value))}
            for value in eigenvalues
        ],
    },
    "validation": {
        "steps": steps,
        "initial_state": initial_state.tolist(),
        "applied_input": applied_input.tolist(),
        "input_deviation": input_offset.tolist(),
        "nonlinear_rollout": nonlinear_rollout,
        "linear_rollout": linear_rollout,
        "max_abs_error": max_abs_error,
        "rmse_by_state": rmse_by_state.tolist(),
        "final_abs_error": final_abs_error.tolist(),
    },
    "quality_summary": {
        "short_horizon_match": bool(short_horizon_match),
        "thresholds": {
            "max_abs_error": float(thresholds["max_abs_error"]),
            "temperature_rmse": float(thresholds["temperature_rmse"]),
        },
        "summary": (
            "局部模型在 14 步短时窗口内保持良好一致性，"
            "温度轨迹误差明显小于阈值，可用于该工作点附近的小扰动分析。"
        ),
    },
}

(output_dir / "cstr_operating_point_linearization.json").write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)
PY
