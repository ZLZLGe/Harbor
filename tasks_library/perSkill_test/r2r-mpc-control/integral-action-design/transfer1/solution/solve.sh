#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json
import numpy as np


def load_case():
    with open("/root/transfer1_oven_case.json", "r", encoding="utf-8") as handle:
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
    beta = np.array(cfg["beta"], dtype=float)
    disturbance = np.array(cfg["disturbance"], dtype=float)
    gain = np.array(cfg["nominal_gain"], dtype=float)
    feedforward = np.array(cfg["feedforward"], dtype=float)
    gamma = float(cfg["gamma"])
    c_i = np.array(cfg["c_i"], dtype=float)
    max_integral = np.array(cfg["max_integral"], dtype=float)

    x = np.array(cfg["initial_temperature"], dtype=float)
    integ = np.zeros_like(x)
    clip_count = 0
    records = []

    for k in range(steps):
        ref = reference_for_step(cfg, k)
        err = x - ref
        u_nominal = -gain * err + feedforward

        if use_integral:
            pre_clip = gamma * integ - c_i * dt * err
            post_clip = np.clip(pre_clip, -max_integral, max_integral)
            clip_count += int(np.count_nonzero(np.abs(pre_clip - post_clip) > 1e-12))
            integ = post_clip
            u_total = u_nominal + integ
        else:
            integ = np.zeros_like(x)
            u_total = u_nominal

        records.append(
            {
                "k": k,
                "reference": ref.tolist(),
                "temperature": x.tolist(),
                "u_nominal": u_nominal.tolist(),
                "integral": integ.tolist(),
                "u_total": u_total.tolist(),
            }
        )

        x = alpha * x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records, clip_count


def compute_tail_mae(records, tail_window):
    temp = np.array([row["temperature"] for row in records], dtype=float)
    ref = np.array([row["reference"] for row in records], dtype=float)
    return float(np.mean(np.abs(temp[-tail_window:] - ref[-tail_window:])))


def main():
    cfg = load_case()
    tail_window = int(cfg["tail_window"])

    baseline_records, _ = simulate(cfg, use_integral=False)
    controlled_records, clip_count = simulate(cfg, use_integral=True)

    tail_baseline = compute_tail_mae(baseline_records, tail_window)
    tail_controlled = compute_tail_mae(controlled_records, tail_window)
    improvement = 1.0 - tail_controlled / tail_baseline

    arr_temp = np.array([row["temperature"] for row in controlled_records], dtype=float)
    arr_ref = np.array([row["reference"] for row in controlled_records], dtype=float)
    zone_peak = np.max(np.abs(arr_temp - arr_ref), axis=0).tolist()

    with open("/root/transfer1_oven_timeline.json", "w", encoding="utf-8") as handle:
        json.dump({"records": controlled_records}, handle, indent=2)

    report = {
        "scenario": cfg["scenario"],
        "controller": {
            "gamma": float(cfg["gamma"]),
            "c_i": [float(v) for v in cfg["c_i"]],
            "max_integral": [float(v) for v in cfg["max_integral"]],
        },
        "tail_mae_baseline": tail_baseline,
        "tail_mae_controlled": tail_controlled,
        "improvement_ratio": improvement,
        "zone_peak_deviation": zone_peak,
        "integral_clip_count": int(clip_count),
        "timeline_file": "/root/transfer1_oven_timeline.json",
    }

    with open("/root/transfer1_oven_balance_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
PY
