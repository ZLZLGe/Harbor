#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


class CoatingLineSimulator:
    def __init__(self, config_path: str = "/root/coating_line_case.json"):
        self.config_path = Path(config_path)
        self._load_config()
        self.reset()

    def _load_config(self):
        with self.config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        self.dt = float(config["dt"])
        self.duration = float(config["duration"])
        self.switch_time = float(config["switch_time"])
        self.speed_ramp_duration = float(config["speed_ramp_duration"])
        self.initial_state = np.array(config["initial_state"], dtype=float)
        self.models = {}
        for phase in ("pre_ramp", "post_ramp"):
            phase_cfg = config[phase]
            self.models[phase] = {
                "A": np.array(phase_cfg["A"], dtype=float),
                "B": np.array(phase_cfg["B"], dtype=float),
                "reference_state": np.array(phase_cfg["reference_state"], dtype=float),
                "reference_input": np.array(phase_cfg["reference_input"], dtype=float),
                "disturbance": np.array(phase_cfg["disturbance"], dtype=float),
            }

    def reset(self):
        self.time = 0.0
        self.state = self.initial_state.copy()
        return self.state.copy()

    def _speed_alpha(self, time_value: float) -> float:
        if time_value < self.switch_time:
            return 0.0
        return min((time_value - self.switch_time) / self.speed_ramp_duration, 1.0)

    def get_reference(self, time_value: float | None = None):
        if time_value is None:
            time_value = self.time

        alpha = self._speed_alpha(time_value)
        pre = self.models["pre_ramp"]
        post = self.models["post_ramp"]

        reference_state = pre["reference_state"].copy()
        if time_value >= self.switch_time:
            reference_state[1:3] = post["reference_state"][1:3]
        reference_state[4:] = (
            pre["reference_state"][4:]
            + alpha * (post["reference_state"][4:] - pre["reference_state"][4:])
        )
        reference_input = (
            pre["reference_input"]
            + alpha * (post["reference_input"] - pre["reference_input"])
        )
        return reference_state, reference_input

    def get_phase(self, time_value: float | None = None) -> str:
        if time_value is None:
            time_value = self.time
        return "pre_ramp" if time_value < self.switch_time else "post_ramp"

    def get_model(self, time_value: float | None = None):
        phase = self.get_phase(time_value)
        return phase, self.models[phase]

    def step(self, control_input):
        control_input = np.array(control_input, dtype=float)
        phase, model = self.get_model(self.time)
        reference_state, reference_input = self.get_reference(self.time)
        next_reference_state, _ = self.get_reference(self.time + self.dt)

        deviation = self.state - reference_state
        next_deviation = (
            model["A"] @ deviation
            + model["B"] @ (control_input - reference_input)
            + model["disturbance"]
        )
        self.state = next_reference_state + next_deviation
        self.time = round(self.time + self.dt, 10)
        return self.state.copy()


def main():
    sim = CoatingLineSimulator()
    print("Initial state:", sim.reset().tolist())
    for _ in range(5):
        _, u_ref = sim.get_reference()
        x = sim.step(u_ref)
        print(f"t={sim.time:.2f}", x.tolist())


if __name__ == "__main__":
    main()
