#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json
import numpy as np


def load_case():
    with open("/root/transfer2_reservoir_case.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def reference_for_step(cfg, k):
    chosen = cfg["reference_schedule"][0]["ref"]
    for segment in cfg["reference_schedule"]:
        if k >= int(segment["start"]):
            chosen = segment["ref"]
    return np.array(chosen, dtype=float)


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

    x = np.array(cfg["initial_level"], dtype=float)
    integ = np.zeros_like(x)
    records = []

    for k in range(steps):
        ref = reference_for_step(cfg, k)
        err = x - ref
        u_nominal = -gain * err + feedforward

        if use_integral:
            integ = gamma * integ - c_i * dt * err
            integ = np.clip(integ, -max_integral, max_integral)
            u_total = u_nominal + integ
        else:
            integ = np.zeros_like(x)
            u_total = u_nominal

        records.append(
            {
                "k": k,
                "reference": ref.tolist(),
                "level": x.tolist(),
                "u_nominal": u_nominal.tolist(),
                "integral": integ.tolist(),
                "u_total": u_total.tolist(),
            }
        )

        x = alpha * x + coupling @ x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records


def tail_rmse(records, tail_window):
    level = np.array([row["level"] for row in records], dtype=float)
    ref = np.array([row["reference"] for row in records], dtype=float)
    err = level[-tail_window:] - ref[-tail_window:]
    return float(np.sqrt(np.mean(err * err)))


def main():
    cfg = load_case()
    tail_window = int(cfg["tail_window"])

    baseline = simulate(cfg, use_integral=False)
    controlled = simulate(cfg, use_integral=True)

    baseline_rmse = tail_rmse(baseline, tail_window)
    controlled_rmse = tail_rmse(controlled, tail_window)
    improvement = 1.0 - controlled_rmse / baseline_rmse

    arr_level = np.array([row["level"] for row in controlled], dtype=float)
    arr_ref = np.array([row["reference"] for row in controlled], dtype=float)
    overshoot = np.max(np.abs(arr_level - arr_ref), axis=0).tolist()
    integral_arr = np.array([row["integral"] for row in controlled], dtype=float)
    integral_energy = float(np.mean(np.sum(integral_arr * integral_arr, axis=1)))

    with open("/root/transfer2_reservoir_trace.json", "w", encoding="utf-8") as handle:
        json.dump({"records": controlled}, handle, indent=2)

    report = {
        "scenario": cfg["scenario"],
        "controller": {
            "gamma": float(cfg["gamma"]),
            "c_i": [float(v) for v in cfg["c_i"]],
            "max_integral": [float(v) for v in cfg["max_integral"]],
        },
        "baseline_tail_rmse": baseline_rmse,
        "controlled_tail_rmse": controlled_rmse,
        "improvement_ratio": improvement,
        "overshoot_per_tank": overshoot,
        "integral_energy": integral_energy,
        "trace_file": "/root/transfer2_reservoir_trace.json",
    }

    with open("/root/transfer2_reservoir_stability.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
