#!/usr/bin/env python3

import json
import random
from pathlib import Path


class BrineMixerSimulator:
    """First-order conductivity response for a brine mixing tank."""

    def __init__(self, config_path="/root/mixing_station_profile.json"):
        self.config_path = Path(config_path)
        self._load_config()
        self._reset_state()

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.initial_conductivity_ms_cm = float(config["initial_conductivity_ms_cm"])
        self.noise_std_ms_cm = float(config["noise_std_ms_cm"])
        self.sample_period_s = float(config["sample_period_s"])
        self.minimum_baseline_s = float(config["minimum_baseline_s"])
        self.minimum_hold_s = float(config["minimum_hold_s"])
        self.max_safe_conductivity_ms_cm = float(config["max_safe_conductivity_ms_cm"])
        self.recommended_step_window_lpm = tuple(config["recommended_step_window_lpm"])
        self.max_pump_lpm = float(config["max_pump_lpm"])
        self.random_seed = int(config["random_seed"])

        self._gain_ms_cm_per_lpm = 0.96
        self._time_constant_s = 44.0

    def _reset_state(self):
        self.time_s = 0.0
        self.conductivity_ms_cm = self.initial_conductivity_ms_cm
        self.brine_pump_lpm = 0.0
        self.safety_limited = False
        self._rng = random.Random(self.random_seed)

    def _measurement(self):
        measured = self.conductivity_ms_cm + self._rng.gauss(0.0, self.noise_std_ms_cm)
        return round(measured, 4)

    def _snapshot(self):
        return {
            "time_s": round(self.time_s, 3),
            "conductivity_ms_cm": self._measurement(),
            "brine_pump_lpm": round(self.brine_pump_lpm, 3),
        }

    def reset(self):
        self._reset_state()
        return self._snapshot()

    def step(self, brine_pump_lpm):
        command = max(0.0, min(float(brine_pump_lpm), self.max_pump_lpm))

        if self.conductivity_ms_cm >= self.max_safe_conductivity_ms_cm:
            command = 0.0
            self.safety_limited = True

        self.brine_pump_lpm = command
        target_conductivity = (
            self.initial_conductivity_ms_cm
            + self._gain_ms_cm_per_lpm * self.brine_pump_lpm
        )
        alpha = self.sample_period_s / self._time_constant_s
        self.conductivity_ms_cm += alpha * (
            target_conductivity - self.conductivity_ms_cm
        )
        self.time_s += self.sample_period_s

        sample = self._snapshot()
        sample["safety_limited"] = self.safety_limited
        return sample

    def get_visible_profile(self):
        return {
            "initial_conductivity_ms_cm": self.initial_conductivity_ms_cm,
            "noise_std_ms_cm": self.noise_std_ms_cm,
            "sample_period_s": self.sample_period_s,
            "minimum_baseline_s": self.minimum_baseline_s,
            "minimum_hold_s": self.minimum_hold_s,
            "recommended_step_window_lpm": list(self.recommended_step_window_lpm),
            "max_safe_conductivity_ms_cm": self.max_safe_conductivity_ms_cm,
            "max_pump_lpm": self.max_pump_lpm,
        }


def main():
    simulator = BrineMixerSimulator()
    print(json.dumps(simulator.get_visible_profile(), indent=2))


if __name__ == "__main__":
    main()
