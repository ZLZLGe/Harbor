#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json
import numpy as np


def load_case():
    with open("/root/similar_line_case.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def ref_for_step(cfg, k):
    if k < int(cfg["switch_step"]):
        return np.array(cfg["reference_initial"], dtype=float)
    return np.array(cfg["reference_final"], dtype=float)


def simulate(cfg, use_integral):
    steps = int(cfg["steps"])
    dt = float(cfg["dt"])
    alpha = np.array(cfg["alpha"], dtype=float)
    beta = np.array(cfg["beta"], dtype=float)
    disturbance = np.array(cfg["disturbance"], dtype=float)
    gain = np.array(cfg["nominal_gain"], dtype=float)
    u_bias = np.array(cfg["u_bias"], dtype=float)
    gamma = float(cfg["gamma"])
    c_i = np.array(cfg["c_i"], dtype=float)
    max_integral = np.array(cfg["max_integral"], dtype=float)

    x = np.array(cfg["initial_state"], dtype=float)
    integ = np.zeros_like(x)
    records = []

    for k in range(steps):
        ref = ref_for_step(cfg, k)
        err = x - ref
        u_mpc = -gain * err + u_bias

        if use_integral:
            integ = gamma * integ - c_i * dt * err
            integ = np.clip(integ, -max_integral, max_integral)
            u_total = u_mpc + integ
        else:
            integ = np.zeros_like(x)
            u_total = u_mpc

        records.append(
            {
                "k": k,
                "reference": ref.tolist(),
                "state": x.tolist(),
                "u_mpc": u_mpc.tolist(),
                "integral": integ.tolist(),
                "u_total": u_total.tolist(),
            }
        )

        x = alpha * x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records


def tail_mae(records, tail_window):
    arr_state = np.array([row["state"] for row in records], dtype=float)
    arr_ref = np.array([row["reference"] for row in records], dtype=float)
    return float(np.mean(np.abs(arr_state[-tail_window:] - arr_ref[-tail_window:])))


def main():
    cfg = load_case()
    tail_window = int(cfg["tail_window"])

    baseline_records = simulate(cfg, use_integral=False)
    controlled_records = simulate(cfg, use_integral=True)

    baseline_tail = tail_mae(baseline_records, tail_window)
    controlled_tail = tail_mae(controlled_records, tail_window)
    improvement = 1.0 - controlled_tail / baseline_tail
    max_abs_integral = float(
        np.max(np.abs(np.array([row["integral"] for row in controlled_records], dtype=float)))
    )

    with open("/root/similar_tension_trace.json", "w", encoding="utf-8") as handle:
        json.dump({"records": controlled_records}, handle, indent=2)

    report = {
        "scenario": cfg["scenario"],
        "controller": {
            "gamma": float(cfg["gamma"]),
            "c_i": [float(v) for v in cfg["c_i"]],
            "max_integral": [float(v) for v in cfg["max_integral"]],
        },
        "kpis": {
            "baseline_tail_mae": baseline_tail,
            "controlled_tail_mae": controlled_tail,
            "improvement_ratio": improvement,
            "max_abs_integral": max_abs_integral,
        },
        "final_state": controlled_records[-1]["state"],
        "final_reference": controlled_records[-1]["reference"],
        "trace_file": "/root/similar_tension_trace.json",
    }

    with open("/root/similar_tension_offset_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
