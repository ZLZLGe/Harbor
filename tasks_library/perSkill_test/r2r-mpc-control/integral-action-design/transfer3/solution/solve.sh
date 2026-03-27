#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json
import math
import numpy as np


def load_case():
    with open("/root/transfer3_winder_case.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def reference_for_step(cfg, k):
    center = np.array(cfg["reference_center"], dtype=float)
    amp = np.array(cfg["reference_amp"], dtype=float)
    period = float(cfg["reference_period_steps"])
    phase = 2.0 * math.pi * (k / period)
    return center + amp * np.array([math.sin(phase), math.cos(phase)], dtype=float)


def simulate(cfg, use_integral):
    steps = int(cfg["steps"])
    dt = float(cfg["dt"])
    alpha = np.array(cfg["alpha"], dtype=float)
    coupling = np.array(cfg["coupling"], dtype=float)
    beta = np.array(cfg["beta"], dtype=float)
    disturbance = np.array(cfg["disturbance"], dtype=float)
    gain = np.array(cfg["nominal_gain"], dtype=float)
    feedforward = np.array(cfg["feedforward"], dtype=float)
    gamma = float(cfg["gamma"])
    c_i = np.array(cfg["c_i"], dtype=float)
    max_integral = np.array(cfg["max_integral"], dtype=float)

    x = np.array(cfg["initial_state"], dtype=float)
    integ = np.zeros_like(x)
    sat_hits = 0
    records = []

    for k in range(steps):
        ref = reference_for_step(cfg, k)
        err = x - ref
        u_nominal = -gain * err + feedforward

        if use_integral:
            integ = gamma * integ - c_i * dt * err
            integ = np.clip(integ, -max_integral, max_integral)
            sat_hits += int(np.any(np.abs(integ) >= max_integral - 1e-12))
            u_total = u_nominal + integ
        else:
            integ = np.zeros_like(x)
            u_total = u_nominal

        records.append(
            {
                "k": k,
                "reference": ref.tolist(),
                "state": x.tolist(),
                "u_nominal": u_nominal.tolist(),
                "integral": integ.tolist(),
                "u_total": u_total.tolist(),
            }
        )

        x = alpha * x + coupling @ x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records, sat_hits / steps


def cycle_mae(records, tail_window):
    state = np.array([row["state"] for row in records], dtype=float)
    ref = np.array([row["reference"] for row in records], dtype=float)
    return float(np.mean(np.abs(state[-tail_window:] - ref[-tail_window:])))


def main():
    cfg = load_case()
    tail_window = int(cfg["tail_window"])

    baseline, _ = simulate(cfg, use_integral=False)
    controlled, sat_fraction = simulate(cfg, use_integral=True)

    baseline_mae = cycle_mae(baseline, tail_window)
    controlled_mae = cycle_mae(controlled, tail_window)
    improvement = 1.0 - controlled_mae / baseline_mae
    control_effort_l1 = float(
        np.sum(np.abs(np.array([row["u_total"] for row in controlled], dtype=float)))
    )

    with open("/root/transfer3_winder_trace.json", "w", encoding="utf-8") as handle:
        json.dump({"records": controlled}, handle, indent=2)

    report = {
        "scenario": cfg["scenario"],
        "controller": {
            "gamma": float(cfg["gamma"]),
            "c_i": [float(v) for v in cfg["c_i"]],
            "max_integral": [float(v) for v in cfg["max_integral"]],
        },
        "baseline_cycle_mae": baseline_mae,
        "controlled_cycle_mae": controlled_mae,
        "improvement_ratio": improvement,
        "control_effort_l1": control_effort_l1,
        "integral_saturation_fraction": float(sat_fraction),
        "trace_file": "/root/transfer3_winder_trace.json",
    }

    with open("/root/transfer3_winder_quality.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
