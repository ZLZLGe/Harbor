#!/usr/bin/env python3
"""
Bench-top incubator thermal simulator.

The chamber is modeled as a first-order thermal system:
    dT/dt = (1 / tau) * (T_base + K * u - T)

`u` is heater command in percent. The true K and tau are hidden.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def _derive_param(seed: str, scale: float, offset: float) -> float:
    value = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return offset + (value % 1_000_000) / 1_000_000.0 * scale


_GAIN_C_PER_PERCENT = _derive_param("incubator_gain_2026", 0.0, 0.095)
_TIME_CONSTANT_SEC = _derive_param("incubator_tau_2026", 0.0, 95.0)


class IncubatorSimulator:
    def __init__(self, config_path: str = "/root/incubator_profile.json") -> None:
        self.config_path = Path(config_path)
        self._load_config()
        self._reset_state()

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.K = _GAIN_C_PER_PERCENT
        self.tau = _TIME_CONSTANT_SEC

        self.baseline_temp = config["baseline_temp_c"]
        self.nominal_culture_temp = config["nominal_culture_temp_c"]
        self.noise_std = config["noise_std_c"]
        self.max_safe_temp = config["max_safe_temp_c"]
        self.min_safe_temp = config["min_safe_temp_c"]
        self.dt = config["dt_sec"]

    def _reset_state(self) -> None:
        self.time = 0.0
        self.temperature = self.baseline_temp
        self.heater_percent = 0.0
        self.safety_cutoff = False

    def _measure(self) -> float:
        return float(self.temperature + np.random.normal(0.0, self.noise_std))

    def reset(self) -> float:
        self._reset_state()
        return self._measure()

    def get_dt(self) -> float:
        return float(self.dt)

    def get_safety_limit(self) -> float:
        return float(self.max_safe_temp)

    def get_baseline_temp(self) -> float:
        return float(self.baseline_temp)

    def step(self, heater_percent: float) -> dict:
        heater_percent = float(np.clip(heater_percent, 0.0, 100.0))

        if self.temperature >= self.max_safe_temp:
            heater_percent = 0.0
            self.safety_cutoff = True

        self.heater_percent = heater_percent
        dtemp_dt = (self.baseline_temp + self.K * heater_percent - self.temperature) / self.tau
        self.temperature += dtemp_dt * self.dt
        self.time += self.dt

        return {
            "time_s": round(self.time, 2),
            "temperature_c": round(self._measure(), 4),
            "heater_percent": round(self.heater_percent, 2),
            "safety_cutoff": self.safety_cutoff,
        }


def main() -> None:
    sim = IncubatorSimulator()
    print(f"baseline={sim.get_baseline_temp():.2f}C safety_limit={sim.get_safety_limit():.2f}C dt={sim.get_dt():.1f}s")
    sim.reset()
    for _ in range(5):
        print(sim.step(30.0))


if __name__ == "__main__":
    main()
