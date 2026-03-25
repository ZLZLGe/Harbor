#!/usr/bin/env python3
"""Nominal predictive-control scaffold for the coating-line retrofit task."""

from __future__ import annotations

import numpy as np

from coating_line_env import CoatingLineSimulator, linearize_nominal_model, summarize_trace


def finite_horizon_lqr_control(A, B, Q, R, horizon, initial_error):
    """Return the first control move from a finite-horizon quadratic program."""
    riccati = Q.copy()
    gain = np.zeros((B.shape[1], A.shape[0]), dtype=float)
    for _ in range(horizon - 1):
        gain = np.linalg.solve(R + B.T @ riccati @ B, B.T @ riccati @ A)
        riccati = Q + A.T @ riccati @ (A - B @ gain)
    return -gain @ initial_error


class NominalPredictiveController:
    """Provided controller without integral action."""

    def __init__(self, horizon=8):
        self.horizon = int(horizon)
        self.Q = np.diag([18.0, 18.0, 16.0, 16.0, 0.30, 0.30, 0.25, 0.25])
        self.R = np.diag([0.05, 0.05, 0.05, 0.05])

    def reset(self):
        return None

    def compute_control(self, state, state_ref, torque_ref, dt):
        A, B = linearize_nominal_model(state_ref, dt)
        delta_u = finite_horizon_lqr_control(A, B, self.Q, self.R, self.horizon, state - state_ref)
        return torque_ref + delta_u


def run_case(case_id, controller):
    simulator = CoatingLineSimulator(case_id)
    controller.reset()
    trace = []

    for _ in range(simulator.total_steps):
        state = simulator.get_state()
        state_ref, torque_ref = simulator.get_reference()
        torques = np.asarray(
            controller.compute_control(state, state_ref, torque_ref, simulator.dt),
            dtype=float,
        )
        simulator.step(torques)
        integral_state = getattr(controller, "integral_state", np.zeros(4, dtype=float))
        trace.append(
            {
                "time": round(simulator.get_time(), 4),
                "tensions": simulator.get_state()[:4].tolist(),
                "reference_tensions": state_ref[:4].tolist(),
                "torques": torques.tolist(),
                "integral_state": np.asarray(integral_state, dtype=float).tolist(),
            }
        )

    return trace


def run_baseline_case(case_id):
    controller = NominalPredictiveController()
    trace = run_case(case_id, controller)
    metrics = summarize_trace(trace)
    return trace, metrics
