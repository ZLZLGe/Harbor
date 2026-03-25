#!/usr/bin/env python3

import csv
from pathlib import Path

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parent


def _resolve_path(filename: str) -> Path:
    root_candidate = Path("/root") / filename
    try:
        if root_candidate.exists():
            return root_candidate
    except PermissionError:
        pass
    return ROOT / filename


def _round(value: float) -> float:
    return round(float(value), 6)


def load_model_bundle(path: str | None = None):
    model_path = Path(path) if path is not None else _resolve_path("tank_model.yaml")
    with model_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_case_library(path: str | None = None):
    model = load_model_bundle()
    cases_path = Path(path) if path is not None else _resolve_path("tank_cases.csv")
    cases = {}
    with cases_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_id = row["case_id"]
            cases[case_id] = {
                "description": row["description"],
                "duration_steps": int(row["duration_steps"]),
                "duration_min": _round(int(row["duration_steps"]) * float(model["sample_time_min"])),
                "initial_level_m": float(row["initial_level_m"]),
                "target_before_m": float(row["target_before_m"]),
                "target_after_m": float(row["target_after_m"]),
                "switch_step": int(row["switch_step"]),
                "switch_min": _round(int(row["switch_step"]) * float(model["sample_time_min"])),
                "planned_draw_before_m": float(row["planned_draw_before_m"]),
                "planned_draw_after_m": float(row["planned_draw_after_m"]),
                "planned_draw_switch_step": int(row["planned_draw_switch_step"]),
                "planned_draw_switch_min": _round(
                    int(row["planned_draw_switch_step"]) * float(model["sample_time_min"])
                ),
                "leak_bias_m": float(row["leak_bias_m"]),
            }
    return {"dt_min": float(model["sample_time_min"]), "cases": cases}


class SurgeTankSimulator:
    def __init__(self, case_id: str):
        self.model = load_model_bundle()
        self.case = load_case_library()["cases"][case_id]
        self.case_id = case_id
        self.reset()

    def reset(self):
        self.step_index = 0
        self.level_m = float(self.case["initial_level_m"])
        self.time_min = 0.0
        return self.get_measurement()

    def _target_for_step(self, step_index: int) -> float:
        if step_index < int(self.case["switch_step"]):
            return float(self.case["target_before_m"])
        return float(self.case["target_after_m"])

    def _planned_draw_for_step(self, step_index: int) -> float:
        if step_index < int(self.case["planned_draw_switch_step"]):
            return float(self.case["planned_draw_before_m"])
        return float(self.case["planned_draw_after_m"])

    def get_measurement(self):
        return {
            "time_min": _round(self.time_min),
            "level_m": _round(self.level_m),
            "target_level_m": _round(self._target_for_step(self.step_index)),
            "planned_draw_bias_m": _round(self._planned_draw_for_step(self.step_index)),
        }

    def step(self, valve_pct: float):
        valve_pct = float(np.clip(valve_pct, 0.0, float(self.model["physical_valve_max_pct"])))
        draw_bias = self._planned_draw_for_step(self.step_index)
        self.level_m = float(
            np.clip(
                float(self.model["a_real"]) * self.level_m
                + float(self.model["b_real"]) * valve_pct
                + float(self.model["bias_real"])
                + draw_bias
                + float(self.case["leak_bias_m"]),
                float(self.model["min_level_m"]),
                float(self.model["max_level_m"]),
            )
        )
        self.step_index += 1
        self.time_min = self.step_index * float(self.model["sample_time_min"])
        return self.get_measurement()


def summarize_trace(trace, case_def=None, model=None):
    if model is None:
        model = load_model_bundle()
    if case_def is None:
        raise ValueError("case_def is required for summarize_trace")

    levels = np.array([entry["level_m"] for entry in trace], dtype=float)
    targets = np.array([entry["target_level_m"] for entry in trace], dtype=float)
    valves = np.array([entry["valve_pct"] for entry in trace], dtype=float)
    errors = np.abs(levels - targets)

    tail_window = int(model["tail_window_steps"])
    tail_errors = errors[-tail_window:]
    switch_step = int(case_def["switch_step"])
    switched_levels = levels[switch_step:]

    recovery_time = None
    for idx in range(switch_step, len(trace)):
        if np.all(errors[idx:] <= float(model["recovery_band_m"])):
            recovery_time = _round(
                (idx + 1 - switch_step) * float(model["sample_time_min"])
            )
            break

    peak_overshoot = 0.0
    if switched_levels.size:
        peak_overshoot = max(
            0.0,
            float(np.max(switched_levels - float(case_def["target_after_m"]))),
        )

    return {
        "tail_mean_abs_level_error_m": _round(np.mean(tail_errors)),
        "tail_max_abs_level_error_m": _round(np.max(tail_errors)),
        "recovery_time_min": recovery_time,
        "peak_overshoot_m": _round(peak_overshoot),
        "peak_valve_pct": _round(np.max(valves)),
    }


def extract_checkpoints(trace, model=None):
    if model is None:
        model = load_model_bundle()
    checkpoint_interval = int(model["checkpoint_interval_steps"])
    checkpoints = []
    for index in range(checkpoint_interval - 1, len(trace), checkpoint_interval):
        entry = trace[index]
        checkpoints.append(
            {
                "minute": _round(entry["time_min"]),
                "level_m": _round(entry["level_m"]),
                "target_level_m": _round(entry["target_level_m"]),
                "valve_pct": _round(entry["valve_pct"]),
                "integral_state_pct": _round(entry["integral_state_pct"]),
            }
        )
    return checkpoints
