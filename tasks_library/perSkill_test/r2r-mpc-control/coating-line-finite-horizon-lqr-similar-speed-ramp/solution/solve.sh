#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json

import numpy as np

from coating_line_simulator import CoatingLineSimulator


def finite_horizon_gains(A, B, Q, R, horizon, terminal_cost=None):
    terminal = Q if terminal_cost is None else terminal_cost
    P = terminal.copy()
    gains = []
    for _ in range(horizon):
        K = np.linalg.solve(R + B.T @ P @ B, B.T @ P @ A)
        gains.append(K)
        P = Q + A.T @ P @ (A - B @ K)
    gains.reverse()
    return gains


def sampled_gain_summary(phase, gains):
    horizon = len(gains)
    indices = [0, horizon // 2, horizon - 1]
    sample = []
    for stage in indices:
        sample.append(
            {
                "stage": int(stage),
                "fro_norm": float(np.linalg.norm(gains[stage], ord="fro")),
            }
        )
    return {"phase": phase, "horizon": horizon, "sampled_stage_gains": sample}


def compute_metrics(trajectory, dt, duration, switch_time):
    tensions = np.array([entry["tensions"] for entry in trajectory], dtype=float)
    speeds = np.array([entry["speeds"] for entry in trajectory], dtype=float)
    ref_tensions = np.array([entry["reference_tensions"] for entry in trajectory], dtype=float)
    ref_speeds = np.array([entry["reference_speeds"] for entry in trajectory], dtype=float)
    controls = np.array([entry["control_inputs"] for entry in trajectory], dtype=float)
    times = np.array([entry["time"] for entry in trajectory], dtype=float)

    steady_mask = times >= duration - 1.0 - 1e-9
    switch_mask = times >= switch_time - 1e-9

    return {
        "steady_state_tension_error": float(
            np.mean(np.abs(tensions[steady_mask] - ref_tensions[steady_mask]))
        ),
        "steady_state_speed_error": float(
            np.mean(np.abs(speeds[steady_mask] - ref_speeds[steady_mask]))
        ),
        "middle_zone_tension_overshoot": float(
            np.max(
                np.maximum(
                    tensions[switch_mask][:, 1:3] - ref_tensions[switch_mask][:, 1:3],
                    0.0,
                )
            )
        ),
        "line_speed_overshoot": float(
            np.max(np.maximum(speeds[switch_mask] - ref_speeds[switch_mask], 0.0))
        ),
        "control_energy": float(np.sum(dt * np.sum(controls * controls, axis=1))),
    }


def main():
    simulator = CoatingLineSimulator("/root/coating_line_case.json")
    simulator.reset()

    horizon = 16
    Q = np.diag([22.0, 30.0, 30.0, 22.0, 110.0, 110.0, 110.0, 110.0])
    R = np.diag([0.6, 0.6, 0.6, 0.6])

    phase_gains = {}
    phase_summary = []
    for phase in ("pre_ramp", "post_ramp"):
        model = simulator.models[phase]
        gains = finite_horizon_gains(model["A"], model["B"], Q, R, horizon)
        phase_gains[phase] = gains
        phase_summary.append(sampled_gain_summary(phase, gains))

    total_steps = int(round(simulator.duration / simulator.dt))
    trajectory = []

    for _ in range(total_steps):
        phase = simulator.get_phase()
        reference_state, reference_input = simulator.get_reference()
        gains = phase_gains[phase]
        deviation = simulator.state - reference_state
        control_input = reference_input - gains[0] @ deviation
        control_input = np.clip(control_input, -2.0, 2.0)

        next_state = simulator.step(control_input)
        next_reference, _ = simulator.get_reference()

        trajectory.append(
            {
                "time": float(simulator.time),
                "phase": simulator.get_phase(),
                "tensions": next_state[:4].tolist(),
                "speeds": next_state[4:].tolist(),
                "reference_tensions": next_reference[:4].tolist(),
                "reference_speeds": next_reference[4:].tolist(),
                "control_inputs": control_input.tolist(),
            }
        )

    metrics = compute_metrics(
        trajectory, simulator.dt, simulator.duration, simulator.switch_time
    )

    report = {
        "scenario": {
            "dt": simulator.dt,
            "duration": simulator.duration,
            "switch_time": simulator.switch_time,
        },
        "phase_gain_summary": phase_summary,
        "trajectory": trajectory,
        "metrics": metrics,
    }

    with open("/root/coating_response_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
PY
