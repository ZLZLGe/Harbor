#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "oven_cases.json"
MODEL_PATH = ROOT / "heater_model.json"


def load_case_library():
    with CASE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_model_bundle():
    with MODEL_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class TwoZoneOven:
    def __init__(self):
        model = load_model_bundle()
        self.dt = float(model["sample_time_sec"])
        self.heater_power_limit_kw = np.array(model["heater_power_limit_kw"], dtype=float)

        self.ambient_temp_c = 24.0
        self.loss_coeff = np.array([0.03, 0.028], dtype=float)
        self.coupling_coeff = 0.016
        self.heater_gain = np.array([1.2, 1.05], dtype=float)
        self.heat_capacity = np.array([180.0, 220.0], dtype=float)

        self.case_library = load_case_library()["cases"]
        self._reset_internal()

    def _reset_internal(self):
        self.state_c = np.zeros(2, dtype=float)
        self.reference_c = np.zeros(2, dtype=float)
        self.base_load_kw = np.zeros(2, dtype=float)
        self.active_events = []
        self.current_step = 0

    def reset(self, case_id):
        case = self.case_library[case_id]
        self._reset_internal()
        self.state_c = np.array(case["initial_temperature_c"], dtype=float)
        self.reference_c = np.array(case["reference_temperature_c"], dtype=float)
        self.base_load_kw = np.array(case["base_load_kw"], dtype=float)
        self.active_events = list(case.get("events", []))
        self.duration_steps = int(case["duration_steps"])
        return self.state_c.copy(), self.reference_c.copy()

    def get_current_load_kw(self):
        load_kw = self.base_load_kw.copy()
        for event in self.active_events:
            if event["type"] == "load_shift" and self.current_step >= int(event["step"]):
                load_kw = np.array(event["load_kw"], dtype=float)
        return load_kw

    def step(self, heater_power_kw):
        heater_power_kw = np.clip(
            np.array(heater_power_kw, dtype=float),
            np.zeros(2, dtype=float),
            self.heater_power_limit_kw,
        )
        load_kw = self.get_current_load_kw()
        zone_1_rate = (
            -self.loss_coeff[0] * (self.state_c[0] - self.ambient_temp_c)
            + self.coupling_coeff * (self.state_c[1] - self.state_c[0])
            + self.heater_gain[0] * heater_power_kw[0]
            - load_kw[0]
        ) / self.heat_capacity[0]
        zone_2_rate = (
            -self.loss_coeff[1] * (self.state_c[1] - self.ambient_temp_c)
            + self.coupling_coeff * (self.state_c[0] - self.state_c[1])
            + self.heater_gain[1] * heater_power_kw[1]
            - load_kw[1]
        ) / self.heat_capacity[1]
        self.state_c = self.state_c + self.dt * np.array([zone_1_rate, zone_2_rate], dtype=float)
        self.current_step += 1
        return self.state_c.copy(), load_kw


def summarize_trace(trace, tail_window_steps):
    temperatures = np.array([entry["temperatures_c"] for entry in trace], dtype=float)
    references = np.array([entry["reference_temperatures_c"] for entry in trace], dtype=float)
    heater_power = np.array([entry["heater_power_kw"] for entry in trace], dtype=float)
    errors = np.abs(temperatures - references)
    tail_errors = errors[-tail_window_steps:]
    return {
        "tail_mean_abs_error": float(np.mean(tail_errors)),
        "tail_max_abs_error": float(np.max(tail_errors)),
        "peak_temperature_c": float(np.max(temperatures)),
        "peak_heater_power_kw": float(np.max(np.abs(heater_power))),
    }
