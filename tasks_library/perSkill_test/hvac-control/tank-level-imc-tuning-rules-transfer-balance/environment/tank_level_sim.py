#!/usr/bin/env python3
"""Deterministic first-order tank level simulator with constant outflow."""

import json
from pathlib import Path

import numpy as np


class TankLevelSimulator:
    """Liquid-level model with a fixed downstream draw."""

    def __init__(self, config_path="/root/tank_level_case.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.reset()

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reset(self):
        self.time_s = 0.0
        self.level_pct = float(self.config["initial_level_pct"])
        return self.level_pct

    def step(self, valve_open_pct):
        cfg = self.config
        valve_open_pct = float(np.clip(
            valve_open_pct,
            cfg["valve_min_pct"],
            cfg["valve_max_pct"],
        ))

        target_balance_level = (
            cfg["base_level_pct"]
            - cfg["constant_outflow_equivalent_pct"]
            + cfg["process_gain_pct_per_valve_pct"] * valve_open_pct
        )
        dlevel_dt = (target_balance_level - self.level_pct) / cfg["time_constant_s"]
        self.level_pct += dlevel_dt * cfg["dt_s"]
        self.time_s += cfg["dt_s"]

        return {
            "time_s": round(self.time_s, 4),
            "level_pct": round(self.level_pct, 4),
            "valve_open_pct": round(valve_open_pct, 4),
        }


def simulate_pi_controller(config_path, kp, ki):
    simulator = TankLevelSimulator(config_path)
    cfg = simulator.config
    integral = 0.0
    trace = []

    steps = int(cfg["duration_s"] / cfg["dt_s"])
    target_level = cfg["target_level_pct"]

    for _ in range(steps):
        error_pct = target_level - simulator.level_pct
        valve_open_pct = kp * error_pct + ki * integral
        result = simulator.step(valve_open_pct)
        integral += error_pct * cfg["dt_s"]

        trace.append({
            "time_s": result["time_s"],
            "level_pct": result["level_pct"],
            "valve_open_pct": result["valve_open_pct"],
            "error_pct": round(target_level - result["level_pct"], 4),
        })

    return trace


def compute_metrics(trace, target_level_pct, settling_band_pct, steady_state_window_s, dt_s):
    levels = [entry["level_pct"] for entry in trace]
    times = [entry["time_s"] for entry in trace]
    peak_level_pct = max(levels)
    minimum_level_pct = min(levels)

    settling_time_s = times[-1]
    for index in range(len(levels)):
        if all(abs(level - target_level_pct) <= settling_band_pct for level in levels[index:]):
            settling_time_s = times[index]
            break

    window_points = max(1, int(round(steady_state_window_s / dt_s)))
    steady_state_levels = levels[-window_points:]
    steady_state_error_pct = float(np.mean([abs(level - target_level_pct) for level in steady_state_levels]))

    return {
        "settling_time_s": round(float(settling_time_s), 4),
        "steady_state_error_pct": round(steady_state_error_pct, 4),
        "peak_level_pct": round(float(peak_level_pct), 4),
        "minimum_level_pct": round(float(minimum_level_pct), 4),
        "final_level_pct": round(float(levels[-1]), 4),
    }


def required_hold_valve_pct(config):
    return (
        config["target_level_pct"]
        - config["base_level_pct"]
        + config["constant_outflow_equivalent_pct"]
    ) / config["process_gain_pct_per_valve_pct"]


def average_valve_pct_last_window(trace, window_s, dt_s):
    window_points = max(1, int(round(window_s / dt_s)))
    recent = trace[-window_points:]
    return round(float(np.mean([entry["valve_open_pct"] for entry in recent])), 4)


def build_checkpoints(trace, checkpoint_times_s):
    lookup = {round(entry["time_s"], 4): entry for entry in trace}
    checkpoints = []
    for time_s in checkpoint_times_s:
        entry = lookup[round(float(time_s), 4)]
        checkpoints.append({
            "time_s": float(time_s),
            "level_pct": entry["level_pct"],
            "valve_open_pct": entry["valve_open_pct"],
            "error_pct": entry["error_pct"],
        })
    return checkpoints
