#!/usr/bin/env python3
"""4-section coating-line tension simulator used by the retrofit task."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _default_cases_path() -> Path:
    root_path = Path("/root/coating_line_cases.json")
    try:
        if root_path.exists():
            return root_path
    except PermissionError:
        pass
    return Path(__file__).resolve().with_name("coating_line_cases.json")


NOMINAL_PARAMS = {
    "EA": 2100.0,
    "J": np.array([0.75, 0.85, 0.80, 0.70], dtype=float),
    "R": 0.045,
    "fb": np.array([8.0, 8.5, 9.0, 8.0], dtype=float),
    "L": np.array([0.90, 1.10, 1.00, 0.95], dtype=float),
    "v0": 0.55,
}

ACTUAL_PARAMS = {
    "EA": 2100.0,
    "J": np.array([0.78, 0.88, 0.83, 0.74], dtype=float),
    "R": 0.045,
    "fb": np.array([8.6, 9.1, 9.8, 8.7], dtype=float),
    "L": np.array([0.90, 1.12, 1.02, 0.96], dtype=float),
    "v0": 0.55,
}


def load_case_library(cases_path: str | Path | None = None) -> dict:
    path = Path(cases_path) if cases_path is not None else _default_cases_path()
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def compute_reference_velocities(tension_ref, params=None):
    params = NOMINAL_PARAMS if params is None else params
    tension_ref = np.asarray(tension_ref, dtype=float)
    velocities = np.zeros_like(tension_ref, dtype=float)
    v_prev = params["v0"]
    tension_prev = 0.0
    for idx, tension in enumerate(tension_ref):
        velocities[idx] = (params["EA"] - tension_prev) / (params["EA"] - tension) * v_prev
        v_prev = velocities[idx]
        tension_prev = tension
    return velocities


def compute_reference_torques(state_ref, params=None):
    params = ACTUAL_PARAMS if params is None else params
    state_ref = np.asarray(state_ref, dtype=float)
    num_sections = 4
    torques = np.zeros(num_sections, dtype=float)
    tensions = state_ref[:num_sections]
    velocities = state_ref[num_sections:]
    for idx in range(num_sections):
        next_tension = tensions[idx + 1] if idx < num_sections - 1 else 0.0
        torques[idx] = params["fb"][idx] / params["R"] * velocities[idx] - params["R"] * (next_tension - tensions[idx])
    return torques


def get_case_definition(case_id: str, cases_path: str | Path | None = None) -> dict:
    library = load_case_library(cases_path)
    return library["cases"][case_id]


def get_reference_for_time(case_def: dict, time_sec: float):
    use_final = case_def["step_time_sec"] is not None and time_sec >= float(case_def["step_time_sec"])
    tension_ref = np.array(
        case_def["final_tension_ref"] if use_final else case_def["initial_tension_ref"],
        dtype=float,
    )
    velocity_ref = compute_reference_velocities(tension_ref, params=ACTUAL_PARAMS)
    state_ref = np.concatenate([tension_ref, velocity_ref])
    torque_ref = compute_reference_torques(state_ref, params=ACTUAL_PARAMS)
    return state_ref, torque_ref


def linearize_nominal_model(state_ref, dt: float):
    state_ref = np.asarray(state_ref, dtype=float)
    num_sections = 4
    jac_state = np.zeros((8, 8), dtype=float)
    jac_input = np.zeros((8, 4), dtype=float)

    for idx in range(num_sections):
        velocity = state_ref[num_sections + idx]
        tension = state_ref[idx]
        section_length = NOMINAL_PARAMS["L"][idx]

        jac_state[idx, idx] = -velocity / section_length
        jac_state[idx, num_sections + idx] = NOMINAL_PARAMS["EA"] / section_length - tension / section_length
        if idx > 0:
            prev_velocity = state_ref[num_sections + idx - 1]
            prev_tension = state_ref[idx - 1]
            jac_state[idx, idx - 1] = prev_velocity / section_length
            jac_state[idx, num_sections + idx - 1] = -NOMINAL_PARAMS["EA"] / section_length + prev_tension / section_length

        inertia = NOMINAL_PARAMS["J"][idx]
        radius = NOMINAL_PARAMS["R"]
        jac_state[num_sections + idx, idx] = -(radius**2) / inertia
        jac_state[num_sections + idx, num_sections + idx] = -NOMINAL_PARAMS["fb"][idx] / inertia
        if idx < num_sections - 1:
            jac_state[num_sections + idx, idx + 1] = (radius**2) / inertia
        jac_input[num_sections + idx, idx] = radius / inertia

    return np.eye(8, dtype=float) + dt * jac_state, dt * jac_input


def summarize_trace(trace):
    tensions = np.array([entry["tensions"] for entry in trace], dtype=float)
    refs = np.array([entry["reference_tensions"] for entry in trace], dtype=float)
    torques = np.array([entry["torques"] for entry in trace], dtype=float)
    tail_errors = np.abs(tensions[-50:] - refs[-50:])
    return {
        "tail_mean_abs_error": float(np.mean(tail_errors)),
        "tail_max_abs_error": float(np.max(tail_errors)),
        "peak_tension": float(np.max(tensions)),
        "peak_abs_torque": float(np.max(np.abs(torques))),
    }


class CoatingLineSimulator:
    """Plant model with model mismatch and persistent friction bias."""

    def __init__(self, case_id: str, cases_path: str | Path | None = None):
        library = load_case_library(cases_path)
        self.dt = float(library["dt"])
        self.num_sections = int(library["num_sections"])
        self.case_id = case_id
        self.case = library["cases"][case_id]
        self.duration_sec = float(self.case["duration_sec"])
        self.total_steps = int(round(self.duration_sec / self.dt))
        self.friction_bias = np.array(self.case["friction_bias"], dtype=float)
        self.reset()

    def reset(self):
        self.step_index = 0
        ref_state, _ = self.get_reference()
        self.tensions = ref_state[: self.num_sections].copy()
        self.velocities = ref_state[self.num_sections :].copy()
        return self.get_state()

    def get_time(self) -> float:
        return self.step_index * self.dt

    def get_state(self):
        return np.concatenate([self.tensions, self.velocities])

    def get_reference(self):
        return get_reference_for_time(self.case, self.get_time())

    def step(self, torques):
        torques = np.asarray(torques, dtype=float)
        ref_state, _ = self.get_reference()

        v_prev = np.concatenate([[ref_state[self.num_sections]], self.velocities[:-1]])
        t_prev = np.concatenate([[0.0], self.tensions[:-1]])
        d_tension = (ACTUAL_PARAMS["EA"] / ACTUAL_PARAMS["L"]) * (self.velocities - v_prev)
        d_tension += (1.0 / ACTUAL_PARAMS["L"]) * (v_prev * t_prev - self.velocities * self.tensions)

        t_next = np.concatenate([self.tensions[1:], [0.0]])
        effective_torque = torques - self.friction_bias
        d_velocity = (ACTUAL_PARAMS["R"] ** 2 / ACTUAL_PARAMS["J"]) * (t_next - self.tensions)
        d_velocity += (ACTUAL_PARAMS["R"] / ACTUAL_PARAMS["J"]) * effective_torque
        d_velocity -= (ACTUAL_PARAMS["fb"] / ACTUAL_PARAMS["J"]) * self.velocities

        self.tensions = np.maximum(self.tensions + self.dt * d_tension, 0.0)
        self.velocities = self.velocities + self.dt * d_velocity
        self.step_index += 1
        return self.get_state()
