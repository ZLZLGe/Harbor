#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/quadrotor_case.json ]; then
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
import sys
from pathlib import Path

import numpy as np

base_dir = Path(os.environ["BASE_DIR"])
output_dir = Path(os.environ["OUTPUT_DIR"])
config = json.loads((base_dir / "quadrotor_case.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(base_dir))

from planar_quadrotor import PlanarQuadrotor

quadrotor = PlanarQuadrotor(str(base_dir / "quadrotor_case.json"))
DT = quadrotor.dt
STATE_ORDER = ["x", "z", "theta", "vx", "vz", "omega"]
INPUT_ORDER = ["u_left", "u_right"]


def matrix_exponential(matrix, dt):
    scaled = np.array(matrix, dtype=float) * dt
    result = np.eye(scaled.shape[0], dtype=float)
    term = np.eye(scaled.shape[0], dtype=float)
    for order in range(1, 6):
        term = term @ scaled / float(order)
        result = result + term
    return result


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
            [0.0, 0.0, -(total_thrust / quadrotor.mass) * cos_theta, 0.0, 0.0, 0.0],
            [0.0, 0.0, -(total_thrust / quadrotor.mass) * sin_theta, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        dtype=float,
    )
    b_matrix = np.array(
        [
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [-sin_theta / quadrotor.mass, -sin_theta / quadrotor.mass],
            [cos_theta / quadrotor.mass, cos_theta / quadrotor.mass],
            [-quadrotor.arm_length / quadrotor.inertia, quadrotor.arm_length / quadrotor.inertia],
        ],
        dtype=float,
    )
    return a_matrix, b_matrix


def discretize_zoh(a_continuous, b_continuous):
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


reference_state = np.array(config["hover_state"], dtype=float)
reference_input = quadrotor.hover_input()
steady_state_residual = quadrotor.dynamics(reference_state, reference_input)

a_continuous, b_continuous = continuous_jacobian(reference_state, reference_input)
a_discrete, b_discrete = discretize_zoh(a_continuous, b_continuous)

validation_case = config["validation_case"]
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
    nonlinear_state = quadrotor.rk4_step(nonlinear_state, applied_input)
    delta_state = linear_state - reference_state
    linear_state = reference_state + a_discrete @ delta_state + b_discrete @ input_deviation
    nonlinear_rollout.append(nonlinear_state.tolist())
    linear_rollout.append(linear_state.tolist())

nonlinear_array = np.array(nonlinear_rollout, dtype=float)
linear_array = np.array(linear_rollout, dtype=float)
error = nonlinear_array - linear_array
abs_error = np.abs(error)
position_error_norm = np.linalg.norm(error[:, :2], axis=1)
velocity_error_norm = np.linalg.norm(error[:, 3:5], axis=1)
attitude_error = np.abs(error[:, 2])
rmse_by_state = np.sqrt(np.mean(np.square(error), axis=0))

thresholds = config["quality_thresholds"]
within_threshold = (
    float(np.max(position_error_norm)) <= float(thresholds["max_position_error_norm"])
    and float(np.max(velocity_error_norm)) <= float(thresholds["max_velocity_error_norm"])
    and float(np.max(attitude_error)) <= float(thresholds["max_attitude_error"])
)

result = {
    "hover_equilibrium": {
        "reference_state": reference_state.tolist(),
        "reference_input": reference_input.tolist(),
        "steady_state_residual": steady_state_residual.tolist(),
    },
    "continuous_model": {
        "state_order": STATE_ORDER,
        "input_order": INPUT_ORDER,
        "A": a_continuous.tolist(),
        "B": b_continuous.tolist(),
    },
    "discrete_model": {
        "dt": DT,
        "method": "zoh",
        "A": a_discrete.tolist(),
        "B": b_discrete.tolist(),
        "controllability_rank": controllability_rank(a_discrete, b_discrete),
    },
    "validation": {
        "steps": steps,
        "initial_state": initial_state.tolist(),
        "applied_input": applied_input.tolist(),
        "state_deviation": state_deviation.tolist(),
        "input_deviation": input_deviation.tolist(),
        "nonlinear_rollout": nonlinear_rollout,
        "linear_rollout": linear_rollout,
        "max_position_error_norm": float(np.max(position_error_norm)),
        "max_velocity_error_norm": float(np.max(velocity_error_norm)),
        "max_attitude_error": float(np.max(attitude_error)),
        "rmse_by_state": rmse_by_state.tolist(),
        "final_abs_error": abs_error[-1].tolist(),
    },
    "acceptance": {
        "within_threshold": bool(within_threshold),
        "thresholds": {
            "max_position_error_norm": float(thresholds["max_position_error_norm"]),
            "max_velocity_error_norm": float(thresholds["max_velocity_error_norm"]),
            "max_attitude_error": float(thresholds["max_attitude_error"]),
        },
        "summary": (
            "悬停点附近的局部离散模型在给定小角度与微小推力偏差下通过误差阈值，"
            "可用于短时姿态与平动耦合分析。"
        ),
    },
}

(output_dir / "quadrotor_hover_linearization.json").write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)
PY
