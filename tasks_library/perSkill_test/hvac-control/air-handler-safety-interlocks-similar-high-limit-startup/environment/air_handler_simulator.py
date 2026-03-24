#!/usr/bin/env python3
"""Deterministic supply-air heater simulator for startup protection tasks."""

import json
from pathlib import Path


_HEATING_GAIN = 0.16
_TIME_CONSTANT_SEC = 24.0


class AirHandlerSimulator:
    """Simple first-order supply-air temperature model."""

    def __init__(self, config_path: str = "/root/startup_profile.json"):
        self.config_path = Path(config_path)
        self._load_profile()
        self._reset_state()

    def _load_profile(self):
        with open(self.config_path, "r", encoding="utf-8") as fh:
            profile = json.load(fh)

        self.profile = profile
        self.equipment_id = profile["equipment_id"]
        self.initial_supply_temp_c = profile["initial_supply_temp_c"]
        self.ambient_temp_c = profile["ambient_temp_c"]
        self.target_temp_c = profile["target_temp_c"]
        self.high_limit_c = profile["high_limit_c"]
        self.dt_sec = profile["dt_sec"]

    def _reset_state(self):
        self.time_sec = 0.0
        self.supply_temp_c = float(self.initial_supply_temp_c)
        self.heater_command_pct = 0.0

    def reset(self) -> float:
        self._reset_state()
        return round(self.supply_temp_c, 4)

    def read_temperature(self) -> float:
        return round(self.supply_temp_c, 4)

    def get_profile(self) -> dict:
        return dict(self.profile)

    def step(self, heater_command_pct: float) -> dict:
        heater_command_pct = max(0.0, min(100.0, float(heater_command_pct)))
        self.heater_command_pct = heater_command_pct

        dtemp_dt = (
            (_HEATING_GAIN * heater_command_pct) + self.ambient_temp_c - self.supply_temp_c
        ) / _TIME_CONSTANT_SEC
        self.supply_temp_c += dtemp_dt * self.dt_sec
        self.time_sec += self.dt_sec

        return {
            "time_sec": round(self.time_sec, 2),
            "supply_temp_c": round(self.supply_temp_c, 4),
            "heater_command_pct": round(self.heater_command_pct, 4),
        }


def main():
    sim = AirHandlerSimulator()
    print(f"Equipment: {sim.equipment_id}")
    print(f"Initial supply temperature: {sim.reset():.2f}C")
    for _ in range(5):
        result = sim.step(50.0)
        print(result)


if __name__ == "__main__":
    main()
