#!/usr/bin/env python3
"""Deterministic pH dosing simulator for fermentor caustic-control tasks."""

from __future__ import annotations

import json
from pathlib import Path


class PhDosingSimulator:
    """Simple buffered pH process with configurable scenarios."""

    def __init__(self, config_path: str = "/root/dosing_profile.json") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            self.config_path = Path.cwd() / "dosing_profile.json"
        with self.config_path.open("r", encoding="utf-8") as fh:
            self.profile = json.load(fh)

        self.dt_sec = float(self.profile["dt_sec"])
        self.dosing_gain = float(self.profile["dosing_gain_ph_per_pct_step"])
        self.base_drift = float(self.profile["base_drift_ph_per_step"])
        self.buffer_center = float(self.profile["buffer_center_ph"])
        self.buffer_pull = float(self.profile["buffer_pull_per_step"])

        self.time_sec = 0.0
        self.measured_ph = 7.0
        self.applied_caustic_pct = 0.0

    def reset(self, scenario_name: str) -> float:
        scenario = self.profile[scenario_name]
        self.time_sec = 0.0
        self.measured_ph = float(scenario["initial_ph"])
        self.applied_caustic_pct = 0.0
        return round(self.measured_ph, 4)

    def read_ph(self) -> float:
        return round(self.measured_ph, 4)

    def step(self, applied_caustic_pct: float) -> dict:
        applied_caustic_pct = max(0.0, min(45.0, float(applied_caustic_pct)))
        self.applied_caustic_pct = applied_caustic_pct

        self.measured_ph += self.base_drift
        self.measured_ph += self.dosing_gain * applied_caustic_pct
        self.measured_ph += (self.buffer_center - self.measured_ph) * self.buffer_pull
        self.measured_ph = max(0.0, min(14.0, self.measured_ph))

        self.time_sec += self.dt_sec
        return {
            "time_sec": round(self.time_sec, 2),
            "measured_ph": round(self.measured_ph, 4),
            "applied_caustic_pct": round(self.applied_caustic_pct, 4),
        }

    def get_profile(self) -> dict:
        return self.profile


def main() -> None:
    sim = PhDosingSimulator()
    print(sim.reset("trial_dose"))
    for raw in sim.get_profile()["trial_dose"]["requested_profile_pct"]:
        print(sim.step(raw))


if __name__ == "__main__":
    main()
