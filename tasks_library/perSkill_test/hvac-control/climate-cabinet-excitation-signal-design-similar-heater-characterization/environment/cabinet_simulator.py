#!/usr/bin/env python3
"""
Climate cabinet thermal simulator for open-loop heater characterization.
"""

import json
import random
from pathlib import Path


_HIDDEN_GAIN_C_PER_PERCENT = 0.11
_HIDDEN_TIME_CONSTANT_S = 150.0


class ClimateCabinetSimulator:
    def __init__(self, config_path="/root/cabinet_profile.json"):
        self.config_path = Path(config_path)
        self._load_config()
        self.reset()

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.ambient_temp_c = float(config["ambient_temp_c"])
        self.nominal_start_temp_c = float(config["nominal_start_temp_c"])
        self.sensor_noise_std_c = float(config["sensor_noise_std_c"])
        self.sample_period_s = float(config["sample_period_s"])
        self.max_safe_temp_c = float(config["max_safe_temp_c"])
        self.min_safe_temp_c = float(config["min_safe_temp_c"])
        self.noise_seed = int(config.get("noise_seed", 0))

        self._gain_c_per_percent = _HIDDEN_GAIN_C_PER_PERCENT
        self._time_constant_s = _HIDDEN_TIME_CONSTANT_S

    def reset(self):
        self.time_s = 0.0
        self.temperature_c = self.nominal_start_temp_c
        self.heater_percent = 0.0
        self.safety_cutoff = False
        self._rng = random.Random(self.noise_seed)
        return self.read()

    def _measurement(self):
        return self.temperature_c + self._rng.gauss(0.0, self.sensor_noise_std_c)

    def read(self):
        return {
            "time_s": round(self.time_s, 3),
            "temperature_c": round(self._measurement(), 4),
            "heater_percent": round(self.heater_percent, 3),
            "safety_cutoff": self.safety_cutoff,
        }

    def step(self, heater_percent):
        heater_percent = max(0.0, min(100.0, float(heater_percent)))
        self.safety_cutoff = False

        if self.temperature_c >= self.max_safe_temp_c:
            heater_percent = 0.0
            self.safety_cutoff = True

        self.heater_percent = heater_percent

        equilibrium_temp_c = self.ambient_temp_c + self._gain_c_per_percent * heater_percent
        rate_c_per_s = (equilibrium_temp_c - self.temperature_c) / self._time_constant_s
        self.temperature_c += rate_c_per_s * self.sample_period_s
        self.time_s += self.sample_period_s

        return self.read()

    def get_visible_profile(self):
        return {
            "ambient_temp_c": self.ambient_temp_c,
            "nominal_start_temp_c": self.nominal_start_temp_c,
            "sensor_noise_std_c": self.sensor_noise_std_c,
            "sample_period_s": self.sample_period_s,
            "max_safe_temp_c": self.max_safe_temp_c,
            "min_safe_temp_c": self.min_safe_temp_c,
        }


def main():
    simulator = ClimateCabinetSimulator()
    print(json.dumps(simulator.get_visible_profile(), indent=2))
    print(json.dumps(simulator.reset(), indent=2))
    print(json.dumps(simulator.step(45.0), indent=2))


if __name__ == "__main__":
    main()
