#!/usr/bin/env python3
"""
Conveyor motor speed bench simulator.

The motor is modeled as a first-order speed response:
    domega/dt = (K * u - omega) / tau

`u` is PWM duty in percent. The true K and tau are hidden from the agent.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def _derive_param(seed: str, scale: float, offset: float) -> float:
    value = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return offset + (value % 1_000_000) / 1_000_000.0 * scale


_GAIN_RPM_PER_PERCENT = _derive_param("conveyor_motor_gain_2026", 0.0, 34.8)
_TIME_CONSTANT_SEC = _derive_param("conveyor_motor_tau_2026", 0.0, 0.42)


class ConveyorMotorBench:
    def __init__(self, config_path: str = "/root/motor_bench_config.json") -> None:
        self.config_path = Path(config_path)
        self._load_config()
        self._reset_state()

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.K = _GAIN_RPM_PER_PERCENT
        self.tau = _TIME_CONSTANT_SEC

        self.initial_speed_rpm = config["initial_speed_rpm"]
        self.safe_speed_limit_rpm = config["safe_speed_limit_rpm"]
        self.noise_std_rpm = config["tachometer_noise_std_rpm"]
        self.dt = config["dt_sec"]
        self.recommended_band_rpm = config["recommended_identification_band_rpm"]

    def _reset_state(self) -> None:
        self.time_s = 0.0
        self.speed_rpm = float(self.initial_speed_rpm)
        self.pwm_percent = 0.0
        self.overspeed_trip = False

    def _measure_speed(self) -> float:
        return float(self.speed_rpm + np.random.normal(0.0, self.noise_std_rpm))

    def reset(self) -> float:
        self._reset_state()
        return self._measure_speed()

    def get_dt(self) -> float:
        return float(self.dt)

    def get_safe_speed_limit(self) -> float:
        return float(self.safe_speed_limit_rpm)

    def step(self, pwm_percent: float) -> dict:
        pwm_percent = float(np.clip(pwm_percent, 0.0, 100.0))

        if self.speed_rpm >= self.safe_speed_limit_rpm:
            pwm_percent = 0.0
            self.overspeed_trip = True

        self.pwm_percent = pwm_percent
        target_speed = self.K * self.pwm_percent
        dspeed_dt = (target_speed - self.speed_rpm) / self.tau
        self.speed_rpm += dspeed_dt * self.dt
        self.time_s += self.dt

        return {
            "time_s": round(self.time_s, 4),
            "speed_rpm": round(self._measure_speed(), 4),
            "pwm_percent": round(self.pwm_percent, 2),
            "overspeed_trip": self.overspeed_trip,
        }


def main() -> None:
    bench = ConveyorMotorBench()
    print(
        f"safe_limit={bench.get_safe_speed_limit():.1f}rpm dt={bench.get_dt():.3f}s "
        f"recommended_band={bench.recommended_band_rpm}"
    )
    bench.reset()
    for _ in range(5):
        print(bench.step(35.0))


if __name__ == "__main__":
    main()
