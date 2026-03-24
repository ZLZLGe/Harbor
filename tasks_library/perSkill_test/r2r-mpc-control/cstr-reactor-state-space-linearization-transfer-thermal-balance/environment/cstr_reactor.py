#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


class CSTRReactor:
    def __init__(self, config_path="/root/cstr_case.json"):
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as handle:
            self.config = json.load(handle)

        self.dt = float(self.config["dt"])
        self.feed_concentration = float(self.config["feed_concentration"])
        self.residence_time = float(self.config["residence_time"])
        self.k0 = float(self.config["k0"])
        self.e_over_r = float(self.config["E_over_R"])
        self.feed_temperature = float(self.config["feed_temperature"])
        self.coolant_inlet_temperature = float(self.config["coolant_inlet_temperature"])
        self.heat_release_gain = float(self.config["heat_release_gain"])
        self.cooling_gain = float(self.config["cooling_gain"])

    def reaction_rate(self, state):
        concentration, temperature = state
        return self.k0 * np.exp(-self.e_over_r / temperature) * concentration

    def dynamics(self, state, control):
        concentration, temperature = state
        coolant_flow = float(control[0])
        rate = self.reaction_rate(state)

        dcdt = (self.feed_concentration - concentration) / self.residence_time - rate
        dtdt = (
            (self.feed_temperature - temperature) / self.residence_time
            + self.heat_release_gain * rate
            - self.cooling_gain * coolant_flow * (temperature - self.coolant_inlet_temperature)
        )
        return np.array([dcdt, dtdt], dtype=float)

    def rk4_step(self, state, control):
        state = np.array(state, dtype=float)
        control = np.array(control, dtype=float)

        k1 = self.dynamics(state, control)
        k2 = self.dynamics(state + 0.5 * self.dt * k1, control)
        k3 = self.dynamics(state + 0.5 * self.dt * k2, control)
        k4 = self.dynamics(state + self.dt * k3, control)
        return state + (self.dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


if __name__ == "__main__":
    reactor = CSTRReactor()
    print(json.dumps(reactor.config, indent=2))
