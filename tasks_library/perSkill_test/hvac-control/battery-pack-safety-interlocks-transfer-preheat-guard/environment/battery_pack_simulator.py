#!/usr/bin/env python3
"""Deterministic battery-pack preheat simulator."""

from __future__ import annotations

import json
from pathlib import Path


class BatteryPackSimulator:
    """Simple coupled module and cell thermal model."""

    def __init__(self, config_path: str = "/root/preheat_profile.json") -> None:
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as fh:
            self.profile = json.load(fh)

        self.dt_sec = float(self.profile["dt_sec"])
        self.module_gain = float(self.profile["module_heater_gain_c_per_pct"])
        self.module_tau_sec = float(self.profile["module_time_constant_sec"])
        self.cell_tau_sec = float(self.profile["cell_time_constant_sec"])
        self.ambient_temp_c = float(self.profile["ambient_temp_c"])
        self.cell_bias_c = [float(value) for value in self.profile["cell_bias_c"]]
        self.cell_hotspot_gain_c = [float(value) for value in self.profile["cell_hotspot_gain_c"]]

        self.time_sec = 0.0
        self.module_temp_c = 0.0
        self.cell_temps_c: list[float] = []
        self.heater_pct = 0.0
        self.reset()

    def reset(self) -> dict:
        self.time_sec = 0.0
        self.module_temp_c = float(self.profile["module_initial_temp_c"])
        self.cell_temps_c = [float(value) for value in self.profile["cell_initial_temps_c"]]
        self.heater_pct = 0.0
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "time_sec": round(self.time_sec, 2),
            "module_temp_c": round(self.module_temp_c, 2),
            "cell_temps_c": [round(value, 2) for value in self.cell_temps_c],
            "heater_pct": round(self.heater_pct, 2),
        }

    def step(self, heater_pct: float) -> dict:
        heater_pct = max(0.0, min(100.0, float(heater_pct)))
        self.heater_pct = heater_pct

        module_target = self.ambient_temp_c + (self.module_gain * heater_pct)
        self.module_temp_c += (
            (module_target - self.module_temp_c) * self.dt_sec / self.module_tau_sec
        )

        next_cells = []
        for index, current in enumerate(self.cell_temps_c):
            cell_target = (
                self.module_temp_c
                + self.cell_bias_c[index]
                + (self.cell_hotspot_gain_c[index] * heater_pct / 100.0)
            )
            updated = current + ((cell_target - current) * self.dt_sec / self.cell_tau_sec)
            next_cells.append(updated)
        self.cell_temps_c = next_cells

        self.time_sec += self.dt_sec
        return self.snapshot()

    def get_profile(self) -> dict:
        return self.profile


def main() -> None:
    sim = BatteryPackSimulator()
    print(sim.snapshot())
    for _ in range(5):
        print(sim.step(100.0))


if __name__ == "__main__":
    main()
