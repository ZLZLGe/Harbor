#!/bin/bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$TASK_DIR/environment/microgrid_case.json" ]; then
  ROOT_DIR="$TASK_DIR"
  ENV_DIR="$TASK_DIR/environment"
else
  ROOT_DIR="/root"
  ENV_DIR="/root"
fi

mkdir -p "$ROOT_DIR/artifacts"

export ROOT_DIR
export ENV_DIR

python3 <<'PY'
import json
import os
import sys
from pathlib import Path

import numpy as np

root_dir = Path(os.environ["ROOT_DIR"])
env_dir = Path(os.environ["ENV_DIR"])
sys.path.insert(0, str(env_dir))

from microgrid_droop import (  # noqa: E402
    dynamics,
    load_case,
    load_schedule,
    nominal_reference,
)


def continuous_jacobian(case):
    params = case["model_parameters"]
    _, reference_input = nominal_reference(case)
    active_nominal = float(reference_input[0])
    reactive_nominal = float(reference_input[1])
    nominal_voltage = float(params["nominal_voltage_pu"])

    return (
        np.array(
            [
                [
                    (
                        -1.0
                        - params["active_droop_gain"]
                        * active_nominal
                        * params["active_frequency_coupling"]
                    )
                    / params["tau_frequency"],
                    (
                        -params["active_droop_gain"]
                        * active_nominal
                        * params["active_voltage_exponent"]
                        / nominal_voltage
                    )
                    / params["tau_frequency"],
                ],
                [
                    (
                        -params["reactive_droop_gain"]
                        * reactive_nominal
                        * params["reactive_frequency_coupling"]
                    )
                    / params["tau_voltage"],
                    (
                        -1.0
                        - params["reactive_droop_gain"]
                        * reactive_nominal
                        * params["reactive_voltage_exponent"]
                        / nominal_voltage
                    )
                    / params["tau_voltage"],
                ],
            ],
            dtype=float,
        ),
        np.array(
            [
                [-params["active_droop_gain"] / params["tau_frequency"], 0.0],
                [0.0, -params["reactive_droop_gain"] / params["tau_voltage"]],
            ],
            dtype=float,
        ),
    )


def zoh_discretize(a_matrix, b_matrix, dt):
    num_states, num_inputs = b_matrix.shape
    augmented = np.zeros((num_states + num_inputs, num_states + num_inputs), dtype=float)
    augmented[:num_states, :num_states] = a_matrix
    augmented[:num_states, num_states:] = b_matrix
    eigenvalues, eigenvectors = np.linalg.eig(augmented * dt)
    discrete_augmented = eigenvectors @ np.diag(np.exp(eigenvalues)) @ np.linalg.inv(eigenvectors)
    return (
        np.real_if_close(discrete_augmented[:num_states, :num_states], tol=1000).astype(float),
        np.real_if_close(discrete_augmented[:num_states, num_states:], tol=1000).astype(float),
    )


def sorted_eigenvalue_pairs(values):
    pairs = [
        {"real": float(np.real(value)), "imag": float(np.imag(value))}
        for value in values
    ]
    pairs.sort(key=lambda item: (round(item["real"], 12), round(item["imag"], 12)))
    return pairs


def scheduled_load(schedule, time_s):
    active = schedule[0]["loads"]
    for point in schedule:
        if time_s >= point["time_s"]:
            active = point["loads"]
        else:
            break
    return active.copy()


def rk4_step(state, control, case):
    dt = float(case["dt"])
    k1 = dynamics(state, control, case)
    k2 = dynamics(state + 0.5 * dt * k1, control, case)
    k3 = dynamics(state + 0.5 * dt * k2, control, case)
    k4 = dynamics(state + dt * k3, control, case)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def state_trace(entries):
    return np.array(
        [[entry["frequency_deviation_hz"], entry["voltage_deviation_pu"]] for entry in entries],
        dtype=float,
    )


case = load_case(env_dir / "microgrid_case.json")
schedule = load_schedule(env_dir / "load_step_profile.csv")
reference_state, reference_input = nominal_reference(case)
a_continuous, b_continuous = continuous_jacobian(case)
a_discrete, b_discrete = zoh_discretize(a_continuous, b_continuous, float(case["dt"]))
validation_case = case["validation_case"]
steps = int(validation_case["steps"])
initial_state = np.array(validation_case["initial_state"], dtype=float)

nonlinear_state = initial_state.copy()
linear_state = initial_state.copy()
applied_load_sequence = []
nonlinear_rollout = []
linear_rollout = []

for step_idx in range(steps):
    time_s = step_idx * float(case["dt"])
    load = scheduled_load(schedule, time_s)
    nonlinear_state = rk4_step(nonlinear_state, load, case)
    linear_state = a_discrete @ linear_state + b_discrete @ (load - reference_input)

    applied_load_sequence.append(
        {"time": float(time_s), "loads": load.tolist()}
    )
    nonlinear_rollout.append(
        {
            "time": float((step_idx + 1) * float(case["dt"])),
            "frequency_deviation_hz": float(nonlinear_state[0]),
            "voltage_deviation_pu": float(nonlinear_state[1]),
        }
    )
    linear_rollout.append(
        {
            "time": float((step_idx + 1) * float(case["dt"])),
            "frequency_deviation_hz": float(linear_state[0]),
            "voltage_deviation_pu": float(linear_state[1]),
        }
    )

nonlinear_array = state_trace(nonlinear_rollout)
linear_array = state_trace(linear_rollout)
gap = np.abs(nonlinear_array - linear_array)
thresholds = case["error_tolerances"]

output = {
    "nominal_operating_point": {
        "state_order": ["delta_f_hz", "delta_v_pu"],
        "input_order": ["P_load_pu", "Q_load_pu"],
        "reference_state": reference_state.tolist(),
        "reference_input": reference_input.tolist(),
        "steady_state_residual": dynamics(reference_state, reference_input, case).tolist(),
    },
    "continuous_small_signal_model": {
        "A": a_continuous.tolist(),
        "B": b_continuous.tolist(),
    },
    "discrete_small_signal_model": {
        "dt": float(case["dt"]),
        "method": "zoh",
        "A": a_discrete.tolist(),
        "B": b_discrete.tolist(),
        "eigenvalues": sorted_eigenvalue_pairs(np.linalg.eigvals(a_discrete)),
    },
    "load_step_validation": {
        "steps": steps,
        "initial_state": initial_state.tolist(),
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
        "final_state_gap": gap[-1].tolist(),
    },
    "assessment": {
        "within_tolerance": bool(
            np.max(gap[:, 0]) <= thresholds["max_abs_frequency_gap_hz"]
            and np.max(gap[:, 1]) <= thresholds["max_abs_voltage_gap_pu"]
            and abs(np.min(nonlinear_array[:, 0]) - np.min(linear_array[:, 0]))
            <= thresholds["frequency_nadir_gap_hz"]
            and abs(np.min(nonlinear_array[:, 1]) - np.min(linear_array[:, 1]))
            <= thresholds["voltage_nadir_gap_pu"]
        ),
        "thresholds": thresholds,
        "summary": "额定负载点附近的小信号模型能够近似描述这次小负载突变后的频率和电压偏差。",
    },
}

output_path = root_dir / "artifacts" / "microgrid_droop_linearization.json"
output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
PY
