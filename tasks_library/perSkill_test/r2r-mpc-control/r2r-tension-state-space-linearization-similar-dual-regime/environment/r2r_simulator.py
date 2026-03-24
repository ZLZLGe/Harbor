#!/usr/bin/env python3
"""
R2R Web Handling Simulator

Simulates a 6-section Roll-to-Roll system with tension-velocity dynamics.

Dynamics:
    dT_i/dt = (EA/L)*(v_i - v_{i-1}) + (1/L)*(v_{i-1}*T_{i-1} - v_i*T_i)
    dv_i/dt = (R^2/J)*(T_{i+1} - T_i) + (R/J)*u_i - (fb/J)*v_i

Where:
    T_i: Web tension in section i (N)
    v_i: Web velocity at roller i (m/s)
    EA: Web material stiffness (N)
    J: Roller inertia (kg*m^2)
    R: Roller radius (m)
    fb: Friction coefficient (N*m*s/rad)
    L: Web section length (m)
    u_i: Motor torque input (N*m)
"""

import json
import numpy as np
from pathlib import Path


class R2RSimulator:
    """6-section Roll-to-Roll web handling simulator."""

    def __init__(self, config_path: str = "/root/dual_regime_config.json"):
        self.config_path = Path(config_path)
        self._load_config()
        self._reset_state()

    def _load_config(self):
        with open(self.config_path, "r") as f:
            config = json.load(f)

        self.EA = config["EA"]
        self.J = config["J"]
        self.R = config["R"]
        self.fb = config["fb"]
        self.L = config["L"]
        self.v0 = config["v0"]
        self.dt = config["dt"]
        self.num_sec = config["num_sections"]

    def _reset_state(self):
        self.T = np.zeros(self.num_sec)
        self.v = np.full(self.num_sec, self.v0)
        self.time = 0.0

    def reset(self, x0=None):
        if x0 is None:
            self._reset_state()
        else:
            x0 = np.asarray(x0, dtype=float)
            self.T = x0[: self.num_sec].copy()
            self.v = x0[self.num_sec :].copy()
            self.time = 0.0
        return self.get_state()

    def step(self, u, inlet_velocity=None):
        u = np.asarray(u, dtype=float)
        if inlet_velocity is None:
            inlet_velocity = self.v0

        v_prev = np.concatenate([[inlet_velocity], self.v[:-1]])
        T_prev = np.concatenate([[0.0], self.T[:-1]])
        dT_dt = (self.EA / self.L) * (self.v - v_prev) + \
                (1.0 / self.L) * (v_prev * T_prev - self.v * self.T)

        T_next = np.concatenate([self.T[1:], [0.0]])
        dv_dt = (self.R**2 / self.J) * (T_next - self.T) + \
                (self.R / self.J) * u - (self.fb / self.J) * self.v

        self.T = np.maximum(self.T + self.dt * dT_dt, 0.0)
        self.v = self.v + self.dt * dv_dt
        self.time += self.dt
        return self.get_state()

    def get_state(self):
        return np.concatenate([self.T, self.v])

    def get_time(self):
        return self.time

    def get_params(self):
        return {
            "EA": self.EA,
            "J": self.J,
            "R": self.R,
            "fb": self.fb,
            "L": self.L,
            "v0": self.v0,
            "dt": self.dt,
            "num_sections": self.num_sec,
        }


def main():
    sim = R2RSimulator()
    print("R2R Simulator initialized")
    print(sim.get_params())


if __name__ == "__main__":
    main()
