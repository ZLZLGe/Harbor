#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/dual_regime_config.json ]; then
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
config = json.loads((base_dir / "dual_regime_config.json").read_text())

DT = config["dt"]
EA = config["EA"]
J = config["J"]
R = config["R"]
FB = config["fb"]
L = config["L"]
V0 = config["v0"]
NUM_SEC = config["num_sections"]


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
    a_discrete = np.eye(2 * NUM_SEC) + DT * a_continuous
    b_discrete = DT * b_continuous
    return a_discrete, b_discrete


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


def local_validation(x_ref, u_ref, a_discrete, b_discrete, case_config):
    state_offset = np.array(case_config["state_offset"], dtype=float)
    control_offset = np.array(case_config["control_offset"], dtype=float)
    steps = int(case_config["steps"])

    initial_state = x_ref + state_offset
    control_input = u_ref + control_offset
    inlet_velocity = x_ref[NUM_SEC]

    nonlinear_state = initial_state.copy()
    linear_state = initial_state.copy()
    nonlinear_rollout = []
    linear_rollout = []

    for _ in range(steps):
        nonlinear_state = nonlinear_step(nonlinear_state, control_input, inlet_velocity)
        delta_state = linear_state - x_ref
        linear_state = x_ref + a_discrete @ delta_state + b_discrete @ control_offset
        nonlinear_rollout.append(nonlinear_state.tolist())
        linear_rollout.append(linear_state.tolist())

    nonlinear_array = np.array(nonlinear_rollout)
    linear_array = np.array(linear_rollout)
    error = np.abs(nonlinear_array - linear_array)

    return {
        "steps": steps,
        "initial_state": initial_state.tolist(),
        "control_input": control_input.tolist(),
        "nonlinear_rollout": nonlinear_rollout,
        "linear_rollout": linear_rollout,
        "max_abs_state_error": float(np.max(error)),
        "mean_abs_tension_error": float(np.mean(error[:, :NUM_SEC])),
        "mean_abs_velocity_error": float(np.mean(error[:, NUM_SEC:])),
    }


result = {
    "dt": DT,
    "regimes": {},
}

for regime_name, regime_config in config["operating_points"].items():
    reference_tensions = np.array(regime_config["reference_tensions"], dtype=float)
    reference_velocities = steady_state_velocities(reference_tensions)
    reference_state = np.concatenate([reference_tensions, reference_velocities])
    reference_input = steady_state_input(reference_state)

    a_continuous, b_continuous = continuous_jacobian(reference_state)
    a_discrete, b_discrete = discretize(a_continuous, b_continuous)
    validation = local_validation(
        reference_state,
        reference_input,
        a_discrete,
        b_discrete,
        config["validation_cases"][regime_name],
    )

    result["regimes"][regime_name] = {
        "reference_state": reference_state.tolist(),
        "reference_input": reference_input.tolist(),
        "continuous_model": {
            "A": a_continuous.tolist(),
            "B": b_continuous.tolist(),
        },
        "discrete_model": {
            "A": a_discrete.tolist(),
            "B": b_discrete.tolist(),
        },
        "validation": validation,
    }

pre = result["regimes"]["pre_change"]
post = result["regimes"]["post_change"]
thresholds = config["error_thresholds"]
validation_passed = all(
    regime["validation"]["max_abs_state_error"] <= thresholds["max_abs_state_error"]
    and regime["validation"]["mean_abs_tension_error"] <= thresholds["mean_abs_tension_error"]
    and regime["validation"]["mean_abs_velocity_error"] <= thresholds["mean_abs_velocity_error"]
    for regime in result["regimes"].values()
)

result["comparison"] = {
    "max_abs_continuous_A_delta": float(
        np.max(np.abs(np.array(pre["continuous_model"]["A"]) - np.array(post["continuous_model"]["A"])))
    ),
    "max_abs_continuous_B_delta": float(
        np.max(np.abs(np.array(pre["continuous_model"]["B"]) - np.array(post["continuous_model"]["B"])))
    ),
    "max_abs_discrete_A_delta": float(
        np.max(np.abs(np.array(pre["discrete_model"]["A"]) - np.array(post["discrete_model"]["A"])))
    ),
    "max_abs_discrete_B_delta": float(
        np.max(np.abs(np.array(pre["discrete_model"]["B"]) - np.array(post["discrete_model"]["B"])))
    ),
    "validation_passed": validation_passed,
    "summary": (
        "pre_change 与 post_change 两个局部模型都能在 8 步窗口内近似预测张力与速度变化，"
        "且换辊后主要差异集中在与第 3 段张力相关的 A 矩阵项。"
    ),
}

(output_dir / "r2r_dual_regime_linearization.json").write_text(json.dumps(result, indent=2))
PY
