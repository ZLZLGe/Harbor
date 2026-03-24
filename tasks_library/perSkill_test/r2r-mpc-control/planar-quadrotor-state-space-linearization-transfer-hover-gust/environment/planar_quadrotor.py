#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np


class PlanarQuadrotor:
    def __init__(self, config_path="/root/quadrotor_case.json"):
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.dt = float(config["dt"])
        self.mass = float(config["mass"])
        self.inertia = float(config["inertia"])
        self.arm_length = float(config["arm_length"])
        self.gravity = float(config["gravity"])
        self.hover_state = np.array(config["hover_state"], dtype=float)

    def hover_input(self):
        hover_thrust = 0.5 * self.mass * self.gravity
        return np.array([hover_thrust, hover_thrust], dtype=float)

    def dynamics(self, state, control):
        x_pos, z_pos, theta, vx, vz, omega = np.asarray(state, dtype=float)
        u_left, u_right = np.asarray(control, dtype=float)
        total_thrust = u_left + u_right

        return np.array(
            [
                vx,
                vz,
                omega,
                -(total_thrust / self.mass) * np.sin(theta),
                (total_thrust / self.mass) * np.cos(theta) - self.gravity,
                (self.arm_length / self.inertia) * (u_right - u_left),
            ],
            dtype=float,
        )

    def rk4_step(self, state, control):
        state = np.asarray(state, dtype=float)
        control = np.asarray(control, dtype=float)

        k1 = self.dynamics(state, control)
        k2 = self.dynamics(state + 0.5 * self.dt * k1, control)
        k3 = self.dynamics(state + 0.5 * self.dt * k2, control)
        k4 = self.dynamics(state + self.dt * k3, control)
        return state + (self.dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


if __name__ == "__main__":
    quadrotor = PlanarQuadrotor()
    print(
        json.dumps(
            {
                "dt": quadrotor.dt,
                "mass": quadrotor.mass,
                "inertia": quadrotor.inertia,
                "arm_length": quadrotor.arm_length,
                "gravity": quadrotor.gravity,
                "hover_state": quadrotor.hover_state.tolist(),
                "hover_input": quadrotor.hover_input().tolist(),
            },
            indent=2,
        )
    )
