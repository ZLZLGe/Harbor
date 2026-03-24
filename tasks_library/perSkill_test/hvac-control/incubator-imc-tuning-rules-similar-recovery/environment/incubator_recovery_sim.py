#!/usr/bin/env python3
"""Incubator recovery simulator for a first-order thermal process."""

import json
from pathlib import Path


class IncubatorRecoverySimulator:
    """Deterministic first-order incubator model."""

    def __init__(self, config_path="/root/incubator_case.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.reset()

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reset(self):
        self.time_s = 0.0
        self.temperature_c = float(self.config["initial_temp_c"])
        return self.temperature_c

    def step(self, heater_power_pct):
        heater_power_pct = float(
            min(
                max(heater_power_pct, self.config["heater_min_pct"]),
                self.config["heater_max_pct"],
            )
        )

        if self.temperature_c >= self.config["max_safe_temp_c"]:
            heater_power_pct = 0.0

        ambient = self.config["ambient_temp_c"]
        process_gain = self.config["process_gain_c_per_percent"]
        tau = self.config["time_constant_s"]
        dt = self.config["dt_s"]

        dtemp_dt = (ambient + process_gain * heater_power_pct - self.temperature_c) / tau
        self.temperature_c += dtemp_dt * dt
        self.time_s += dt

        return {
            "time_s": round(self.time_s, 4),
            "temperature_c": round(self.temperature_c, 4),
            "heater_power_pct": round(heater_power_pct, 4),
        }


def simulate_pi_controller(config_path, kp, ki):
    simulator = IncubatorRecoverySimulator(config_path)
    config = simulator.config
    integral = 0.0
    trace = []

    steps = int(config["duration_s"] / config["dt_s"])
    setpoint = config["setpoint_c"]

    for _ in range(steps):
        error_c = setpoint - simulator.temperature_c
        integral += error_c * config["dt_s"]
        heater_power_pct = kp * error_c + ki * integral
        result = simulator.step(heater_power_pct)
        trace.append({
            "time_s": result["time_s"],
            "temperature_c": result["temperature_c"],
            "heater_power_pct": result["heater_power_pct"],
            "error_c": round(setpoint - result["temperature_c"], 4),
        })

    return trace


def compute_metrics(trace, setpoint_c, settling_band_c, steady_state_window_s, dt_s):
    temperatures = [entry["temperature_c"] for entry in trace]
    times = [entry["time_s"] for entry in trace]
    peak_temperature_c = max(temperatures)
    overshoot_c = max(0.0, peak_temperature_c - setpoint_c)

    settling_time_s = times[-1]
    for index in range(len(temperatures)):
        if all(abs(temp - setpoint_c) <= settling_band_c for temp in temperatures[index:]):
            settling_time_s = times[index]
            break

    window_points = max(1, int(round(steady_state_window_s / dt_s)))
    steady_state_temperatures = temperatures[-window_points:]
    steady_state_error_c = sum(
        abs(temp - setpoint_c) for temp in steady_state_temperatures
    ) / len(steady_state_temperatures)

    return {
        "settling_time_s": round(float(settling_time_s), 4),
        "overshoot_c": round(float(overshoot_c), 4),
        "steady_state_error_c": round(steady_state_error_c, 4),
        "peak_temperature_c": round(float(peak_temperature_c), 4),
        "final_temperature_c": round(float(temperatures[-1]), 4),
    }
