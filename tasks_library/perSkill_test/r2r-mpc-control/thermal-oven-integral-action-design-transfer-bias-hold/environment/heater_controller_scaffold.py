#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np

from thermal_oven_env import TwoZoneOven, load_model_bundle, load_case_library, summarize_trace


ROOT = Path(__file__).resolve().parent
OUTPUT_FILENAME = "heater_integrator_config.json"


def _finite_horizon_gain(A, B, Q, R, horizon_steps):
    P = Q.copy()
    feedback = np.zeros((B.shape[1], A.shape[0]), dtype=float)
    for _ in range(horizon_steps):
        solve_term = R + B.T @ P @ B
        feedback = np.linalg.solve(solve_term, B.T @ P @ A)
        P = Q + A.T @ P @ (A - B @ feedback)
    return feedback


class NominalHeaterController:
    def __init__(self, reference_temperature_c):
        model = load_model_bundle()
        self.dt = float(model["sample_time_sec"])
        self.reference_temperature_c = np.array(reference_temperature_c, dtype=float)
        self.A = np.array(model["A_nominal"], dtype=float)
        self.B = np.array(model["B_nominal"], dtype=float)
        self.Q = np.diag(model["Q_diag"])
        self.R = np.diag(model["R_diag"])
        self.heater_power_limit_kw = np.array(model["heater_power_limit_kw"], dtype=float)
        self.nominal_ambient_temp_c = float(model["nominal_ambient_temp_c"])
        self.nominal_loss_coeff = np.array(model["nominal_loss_coeff"], dtype=float)
        self.nominal_coupling_coeff = float(model["nominal_coupling_coeff"])
        self.nominal_heater_gain = np.array(model["nominal_heater_gain"], dtype=float)
        self.feedback = _finite_horizon_gain(
            self.A,
            self.B,
            self.Q,
            self.R,
            int(model["horizon_steps"]),
        )
        self.feedforward_kw = self._compute_feedforward(reference_temperature_c)

    def _compute_feedforward(self, reference_temperature_c):
        reference_temperature_c = np.array(reference_temperature_c, dtype=float)
        rhs = np.array(
            [
                self.nominal_loss_coeff[0]
                * (reference_temperature_c[0] - self.nominal_ambient_temp_c)
                - self.nominal_coupling_coeff
                * (reference_temperature_c[1] - reference_temperature_c[0]),
                self.nominal_loss_coeff[1]
                * (reference_temperature_c[1] - self.nominal_ambient_temp_c)
                - self.nominal_coupling_coeff
                * (reference_temperature_c[0] - reference_temperature_c[1]),
            ],
            dtype=float,
        )
        return rhs / self.nominal_heater_gain

    def nominal_command(self, measured_temperature_c):
        deviation = np.array(measured_temperature_c, dtype=float) - self.reference_temperature_c
        heater_power_kw = self.feedforward_kw - self.feedback @ deviation
        return np.clip(heater_power_kw, np.zeros(2, dtype=float), self.heater_power_limit_kw)


def _normalize_config(config):
    required = {"integral_gain_by_zone", "leak_by_zone", "integral_limit_by_zone"}
    missing = required - set(config.keys())
    if missing:
        raise ValueError(f"missing config fields: {sorted(missing)}")

    normalized = {}
    for key in required:
        values = np.array(config[key], dtype=float)
        if values.shape != (2,):
            raise ValueError(f"{key} must be length 2")
        normalized[key] = values
    return normalized


def run_case(case_id, config):
    normalized = _normalize_config(config)
    model = load_model_bundle()
    cases = load_case_library()["cases"]
    case = cases[case_id]

    plant = TwoZoneOven()
    temperature_c, reference_temperature_c = plant.reset(case_id)
    controller = NominalHeaterController(reference_temperature_c)
    integral_state_kw = np.zeros(2, dtype=float)
    trace = []

    for step in range(int(case["duration_steps"])):
        error_c = temperature_c - reference_temperature_c
        integral_state_kw = (
            normalized["leak_by_zone"] * integral_state_kw
            - normalized["integral_gain_by_zone"] * error_c * controller.dt / 60.0
        )
        integral_state_kw = np.clip(
            integral_state_kw,
            -normalized["integral_limit_by_zone"],
            normalized["integral_limit_by_zone"],
        )
        nominal_kw = controller.nominal_command(temperature_c)
        heater_power_kw = np.clip(
            nominal_kw + integral_state_kw,
            np.zeros(2, dtype=float),
            controller.heater_power_limit_kw,
        )
        temperature_c, load_kw = plant.step(heater_power_kw)
        trace.append(
            {
                "time_sec": round((step + 1) * controller.dt, 4),
                "temperatures_c": [float(value) for value in temperature_c],
                "reference_temperatures_c": [float(value) for value in reference_temperature_c],
                "heater_power_kw": [float(value) for value in heater_power_kw],
                "integral_state_kw": [float(value) for value in integral_state_kw],
                "load_kw": [float(value) for value in load_kw],
            }
        )

    metrics = summarize_trace(trace, int(model["tail_window_steps"]))
    return trace, metrics


def run_baseline_case(case_id):
    cases = load_case_library()["cases"]
    case = cases[case_id]
    model = load_model_bundle()

    plant = TwoZoneOven()
    temperature_c, reference_temperature_c = plant.reset(case_id)
    controller = NominalHeaterController(reference_temperature_c)
    trace = []

    for step in range(int(case["duration_steps"])):
        heater_power_kw = controller.nominal_command(temperature_c)
        temperature_c, load_kw = plant.step(heater_power_kw)
        trace.append(
            {
                "time_sec": round((step + 1) * controller.dt, 4),
                "temperatures_c": [float(value) for value in temperature_c],
                "reference_temperatures_c": [float(value) for value in reference_temperature_c],
                "heater_power_kw": [float(value) for value in heater_power_kw],
                "integral_state_kw": [0.0, 0.0],
                "load_kw": [float(value) for value in load_kw],
            }
        )

    metrics = summarize_trace(trace, int(model["tail_window_steps"]))
    return trace, metrics


def evaluate_config(config):
    results = {}
    for case_id in load_case_library()["cases"]:
        _, baseline_metrics = run_baseline_case(case_id)
        trace, metrics = run_case(case_id, config)
        results[case_id] = {
            **metrics,
            "baseline_tail_mean_abs_error": baseline_metrics["tail_mean_abs_error"],
            "steps": len(trace),
        }
    return results


def load_output_from_root(root_dir="/root"):
    output_path = Path(root_dir) / OUTPUT_FILENAME
    with output_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
