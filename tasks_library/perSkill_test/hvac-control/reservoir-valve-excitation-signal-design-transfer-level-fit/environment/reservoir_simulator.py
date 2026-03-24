#!/usr/bin/env python3
"""
Reservoir level simulator for single-step valve identification.

The hidden process follows a first-order level response:
    dL/dt = (L0 + K * u - L) / tau

`u` is the inlet valve opening in percent. The true K and tau are hidden.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def _derive_param(seed: str, scale: float, offset: float) -> float:
    value = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return offset + (value % 1_000_000) / 1_000_000.0 * scale


_GAIN_CM_PER_PERCENT = _derive_param("reservoir_level_gain_2026", 0.0, 0.34)
_TIME_CONSTANT_SEC = _derive_param("reservoir_level_tau_2026", 0.0, 160.0)


class ReservoirSimulator:
    def __init__(self, config_path: str = "/root/reservoir_profile.json") -> None:
        self.config_path = Path(config_path)
        self._load_config()
        self._reset_state()

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.K = _GAIN_CM_PER_PERCENT
        self.tau = _TIME_CONSTANT_SEC

        self.initial_level_cm = float(config["initial_level_cm"])
        self.nominal_operating_band_cm = list(config["nominal_operating_band_cm"])
        self.recommended_level_rise_cm = list(config["recommended_level_rise_cm"])
        self.noise_std_cm = float(config["sensor_noise_std_cm"])
        self.overflow_level_cm = float(config["overflow_level_cm"])
        self.minimum_level_cm = float(config["minimum_level_cm"])
        self.dt = float(config["dt_sec"])

    def _reset_state(self) -> None:
        self.time_s = 0.0
        self.level_cm = self.initial_level_cm
        self.valve_open_percent = 0.0
        self.overflow_alarm = False

    def _measure_level(self) -> float:
        return float(self.level_cm + np.random.normal(0.0, self.noise_std_cm))

    def reset(self) -> float:
        self._reset_state()
        return self._measure_level()

    def get_dt(self) -> float:
        return self.dt

    def get_overflow_level(self) -> float:
        return self.overflow_level_cm

    def get_initial_level(self) -> float:
        return self.initial_level_cm

    def step(self, valve_open_percent: float) -> dict:
        valve_open_percent = float(np.clip(valve_open_percent, 0.0, 100.0))

        if self.level_cm >= self.overflow_level_cm:
            valve_open_percent = 0.0
            self.overflow_alarm = True

        self.valve_open_percent = valve_open_percent
        target_level = self.initial_level_cm + self.K * self.valve_open_percent
        dlevel_dt = (target_level - self.level_cm) / self.tau
        self.level_cm += dlevel_dt * self.dt
        self.time_s += self.dt

        return {
            "time_s": round(self.time_s, 2),
            "level_cm": round(self._measure_level(), 4),
            "valve_open_percent": round(self.valve_open_percent, 2),
            "overflow_alarm": self.overflow_alarm,
        }


def main() -> None:
    sim = ReservoirSimulator()
    print(
        f"initial_level={sim.get_initial_level():.2f}cm "
        f"overflow={sim.get_overflow_level():.2f}cm dt={sim.get_dt():.1f}s"
    )
    sim.reset()
    for _ in range(5):
        print(sim.step(36.0))


if __name__ == "__main__":
    main()
