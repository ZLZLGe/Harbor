#!/usr/bin/env python3
"""Deterministic tank fill simulator for the overflow interlock task."""

from __future__ import annotations

import json
from pathlib import Path


class TankFillSimulator:
    """Simple single-tank fill and drain model."""

    def __init__(self, config_path: str = "/root/fill_recipe.json") -> None:
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as fh:
            self.recipe = json.load(fh)

        self.dt_sec = float(self.recipe["dt_sec"])
        self.max_inlet_gain = float(self.recipe["hydraulics"]["max_inlet_gain_pct_per_sec"])
        self.base_outflow = float(self.recipe["hydraulics"]["base_outflow_pct_per_sec"])
        self.overflow_level = float(self.recipe["overflow_level_pct"])
        self.sensor_offsets = list(self.recipe["sensor_offsets_pct"])

        self.time_sec = 0.0
        self.level_pct = 0.0
        self._sample_index = 0

    def reset(self, phase_name: str) -> float:
        phase_cfg = self.recipe[phase_name]
        self.time_sec = 0.0
        self.level_pct = float(phase_cfg["initial_level_pct"])
        self._sample_index = 0
        return self.current_measurement()

    def current_measurement(self) -> float:
        offset = self.sensor_offsets[self._sample_index % len(self.sensor_offsets)]
        measured = max(0.0, min(self.overflow_level, self.level_pct + offset))
        return round(measured, 2)

    def step(self, inlet_pct: float) -> dict:
        inlet_pct = max(0.0, min(100.0, float(inlet_pct)))
        net_rate = (self.max_inlet_gain * inlet_pct / 100.0) - self.base_outflow
        self.level_pct += net_rate * self.dt_sec
        self.level_pct = max(0.0, min(self.overflow_level, self.level_pct))

        self.time_sec += self.dt_sec
        self._sample_index += 1

        return {
            "time_sec": round(self.time_sec, 2),
            "measured_level_pct": self.current_measurement(),
            "true_level_pct": round(self.level_pct, 4),
            "applied_inlet_pct": round(inlet_pct, 2),
        }

    def get_recipe(self) -> dict:
        return self.recipe


def main() -> None:
    sim = TankFillSimulator()
    sim.reset("pulse_test")
    for raw in sim.get_recipe()["pulse_test"]["requested_profile_pct"][:4]:
        result = sim.step(raw)
        print(result)


if __name__ == "__main__":
    main()
