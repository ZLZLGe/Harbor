#!/usr/bin/env python3

import numpy as np

from surge_tank_env import (
    SurgeTankSimulator,
    extract_checkpoints,
    load_case_library,
    load_model_bundle,
    summarize_trace,
)


def _round(value: float) -> float:
    return round(float(value), 6)


def _finite_horizon_gain(a: float, b: float, q: float, r: float, horizon_steps: int) -> float:
    p = float(q)
    feedback = 0.0
    for _ in range(horizon_steps):
        denom = r + b * b * p
        feedback = (b * p * a) / denom
        p = q + a * p * (a - b * feedback)
    return float(feedback)


class NominalValveController:
    def __init__(self):
        model = load_model_bundle()
        self.a_nominal = float(model["a_nominal"])
        self.b_nominal = float(model["b_nominal"])
        self.bias_nominal = float(model["bias_nominal"])
        self.physical_valve_max_pct = float(model["physical_valve_max_pct"])
        self.feedback_gain = _finite_horizon_gain(
            self.a_nominal,
            self.b_nominal,
            float(model["q_level"]),
            float(model["r_valve"]),
            int(model["horizon_steps"]),
        )

    def steady_state_valve_pct(self, target_level_m: float, planned_draw_bias_m: float) -> float:
        required = (
            (1.0 - self.a_nominal) * float(target_level_m)
            - self.bias_nominal
            - float(planned_draw_bias_m)
        ) / self.b_nominal
        return float(required)

    def nominal_command(self, level_m: float, target_level_m: float, planned_draw_bias_m: float):
        command = self.steady_state_valve_pct(target_level_m, planned_draw_bias_m)
        command -= self.feedback_gain * (float(level_m) - float(target_level_m))
        return float(np.clip(command, 0.0, self.physical_valve_max_pct))


def _normalize_settings(controller_settings):
    required = {
        "integral_gain_pct_per_m",
        "integral_leak",
        "integral_limit_pct",
        "valve_max_pct",
    }
    missing = required - set(controller_settings.keys())
    if missing:
        raise ValueError(f"missing controller settings: {sorted(missing)}")

    normalized = {key: float(controller_settings[key]) for key in required}
    if normalized["integral_gain_pct_per_m"] < 0.0:
        raise ValueError("integral_gain_pct_per_m must be non-negative")
    if not (0.0 < normalized["integral_leak"] <= 1.0):
        raise ValueError("integral_leak must be in (0, 1]")
    if normalized["integral_limit_pct"] <= 0.0:
        raise ValueError("integral_limit_pct must be positive")
    if normalized["valve_max_pct"] <= 0.0:
        raise ValueError("valve_max_pct must be positive")
    return normalized


def run_case(case_id: str, controller_settings):
    model = load_model_bundle()
    case_def = load_case_library()["cases"][case_id]
    normalized = _normalize_settings(controller_settings)
    valve_cap = min(normalized["valve_max_pct"], float(model["physical_valve_max_pct"]))
    sim = SurgeTankSimulator(case_id)
    controller = NominalValveController()

    integral_state_pct = 0.0
    trace = []

    for _ in range(int(case_def["duration_steps"])):
        measurement = sim.get_measurement()
        level_m = float(measurement["level_m"])
        target_level_m = float(measurement["target_level_m"])
        planned_draw_bias_m = float(measurement["planned_draw_bias_m"])

        error_m = target_level_m - level_m
        integral_state_pct = float(
            np.clip(
                normalized["integral_leak"] * integral_state_pct
                + normalized["integral_gain_pct_per_m"] * error_m,
                -normalized["integral_limit_pct"],
                normalized["integral_limit_pct"],
            )
        )
        base_valve_pct = controller.nominal_command(
            level_m=level_m,
            target_level_m=target_level_m,
            planned_draw_bias_m=planned_draw_bias_m,
        )
        valve_pct = float(np.clip(base_valve_pct + integral_state_pct, 0.0, valve_cap))

        next_state = sim.step(valve_pct)
        trace.append(
            {
                "time_min": _round(next_state["time_min"]),
                "level_m": _round(next_state["level_m"]),
                "target_level_m": _round(target_level_m),
                "valve_pct": _round(valve_pct),
                "integral_state_pct": _round(integral_state_pct),
            }
        )

    metrics = summarize_trace(trace, case_def=case_def, model=model)
    checkpoints = extract_checkpoints(trace, model=model)
    return trace, metrics, checkpoints


def run_baseline_case(case_id: str):
    return run_case(
        case_id,
        {
            "integral_gain_pct_per_m": 0.0,
            "integral_leak": 1.0,
            "integral_limit_pct": 1.0,
            "valve_max_pct": float(load_model_bundle()["physical_valve_max_pct"]),
        },
    )


def build_case_report(case_id: str, controller_settings):
    _, baseline_metrics, _ = run_baseline_case(case_id)
    _, metrics, checkpoints = run_case(case_id, controller_settings)
    return {
        "baseline_tail_mean_abs_level_error_m": baseline_metrics["tail_mean_abs_level_error_m"],
        **metrics,
        "checkpoints": checkpoints,
    }


def evaluate_report(report):
    controller_settings = report["controller_settings"]
    cases = {}
    for case_id in load_case_library()["cases"]:
        cases[case_id] = build_case_report(case_id, controller_settings)
    return {
        "controller_settings": {
            key: _round(value) for key, value in _normalize_settings(controller_settings).items()
        },
        "cases": cases,
    }
