#!/usr/bin/env python3

import csv
import json
from pathlib import Path

import numpy as np


_GAIN_RPM_PER_V = 372.0
_TIME_CONSTANT_S = 2.2


class FanSpinupSimulator:
    def __init__(self, profile_path: str = "/root/fan_bench_profile.json"):
        self.profile_path = Path(profile_path)
        self._load_profile()
        self._rng = np.random.default_rng(20260325)
        self._reset_state()

    def _load_profile(self):
        with self.profile_path.open("r", encoding="utf-8") as handle:
            profile = json.load(handle)

        self.dt = float(profile["sample_period_s"])
        self.max_drive_voltage_v = float(profile["max_drive_voltage_v"])
        self.soft_rpm_ceiling_rpm = float(profile["soft_rpm_ceiling_rpm"])
        self.noise_std_rpm = float(profile["noise_std_rpm"])

    def _reset_state(self):
        self.time_s = 0.0
        self.drive_voltage_v = 0.0
        self.true_rpm = 0.0

    def reset(self):
        self._reset_state()
        return self._build_sample()

    def _build_sample(self):
        measured_rpm = self.true_rpm + self._rng.normal(0.0, self.noise_std_rpm)
        return {
            "time_s": round(self.time_s, 3),
            "drive_voltage_v": round(self.drive_voltage_v, 3),
            "measured_rpm": round(max(0.0, measured_rpm), 3),
        }

    def step(self, drive_voltage_v: float):
        bounded_voltage = float(np.clip(drive_voltage_v, 0.0, self.max_drive_voltage_v))
        target_rpm = min(_GAIN_RPM_PER_V * bounded_voltage, self.soft_rpm_ceiling_rpm + 120.0)

        self.drive_voltage_v = bounded_voltage
        self.true_rpm += ((target_rpm - self.true_rpm) / _TIME_CONSTANT_S) * self.dt
        self.time_s += self.dt

        return self._build_sample()

    def get_profile(self):
        return {
            "sample_period_s": self.dt,
            "max_drive_voltage_v": self.max_drive_voltage_v,
            "soft_rpm_ceiling_rpm": self.soft_rpm_ceiling_rpm,
            "noise_std_rpm": self.noise_std_rpm,
        }


def write_trace_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["time_s", "drive_voltage_v", "measured_rpm"],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    simulator = FanSpinupSimulator()
    trace = [simulator.reset()]
    for _ in range(20):
        trace.append(simulator.step(0.0))
    for _ in range(200):
        trace.append(simulator.step(7.0))
    write_trace_csv("/root/demo_spinup_trace.csv", trace)
