#!/bin/bash
set -euo pipefail

cd /root

python3 <<'INNERPY'
import json
from pathlib import Path
import numpy as np

CASE_FILE = Path("/root/transfer3_case.json")
TRACE_FILE = Path("/root/transfer3_drone_rollout.json")
REPORT_FILE = Path("/root/transfer3_drone_lqr_report.json")


def load_case(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def backward_riccati(A, B, Q, R, horizon):
    p_seq = [None] * (horizon + 1)
    k_seq = [None] * horizon
    p_seq[horizon] = Q.copy()
    for k in range(horizon - 1, -1, -1):
        s_mat = R + B.T @ p_seq[k + 1] @ B
        k_gain = np.linalg.solve(s_mat, B.T @ p_seq[k + 1] @ A)
        p_now = Q + A.T @ p_seq[k + 1] @ (A - B @ k_gain)
        k_seq[k] = k_gain
        p_seq[k] = p_now
    return k_seq, p_seq


def rollout(A, B, Q, R, gains, x0, steps):
    x = x0.copy()
    records = []
    stage_costs = []
    for k in range(steps):
        gain = gains[min(k, len(gains) - 1)]
        u = -gain @ x
        stage_cost = float(x.T @ Q @ x + u.T @ R @ u)
        records.append({"k": int(k), "x": x.tolist(), "u": u.tolist(), "stage_cost": stage_cost})
        stage_costs.append(stage_cost)
        x = A @ x + B @ u
    terminal_cost = float(x.T @ Q @ x)
    return records, stage_costs, terminal_cost, x


def rollout_zero(A, Q, x0, steps):
    x = x0.copy()
    stage_costs = []
    for _ in range(steps):
        stage_costs.append(float(x.T @ Q @ x))
        x = A @ x
    terminal_cost = float(x.T @ Q @ x)
    return stage_costs, terminal_cost


def main():
    case = load_case(CASE_FILE)
    A = np.array(case["A"], dtype=float)
    B = np.array(case["B"], dtype=float)
    Q = np.diag(np.array(case["Q_diag"], dtype=float))
    R = np.diag(np.array(case["R_diag"], dtype=float))
    x0 = np.array(case["x0"], dtype=float)
    horizon = int(case["horizon_N"])
    steps = int(case["rollout_steps"])

    gains, p_seq = backward_riccati(A, B, Q, R, horizon)
    records, stage_costs, terminal_cost, x_final = rollout(A, B, Q, R, gains, x0, steps)
    base_stage, base_terminal = rollout_zero(A, Q, x0, steps)

    optimized_total = float(sum(stage_costs) + terminal_cost)
    baseline_total = float(sum(base_stage) + base_terminal)
    ratio = float(1.0 - optimized_total / baseline_total)

    trace = {
        "scenario": case["scenario"],
        "records": records,
        "terminal_state": x_final.tolist(),
        "terminal_cost": terminal_cost,
    }
    report = {
        "scenario": case["scenario"],
        "state_dim": int(A.shape[0]),
        "control_dim": int(B.shape[1]),
        "horizon_N": horizon,
        "rollout_steps": steps,
        "first_control": records[0]["u"],
        "gain_fro_norms": [float(np.linalg.norm(g, ord="fro")) for g in gains],
        "optimized_total_cost": optimized_total,
        "baseline_total_cost": baseline_total,
        "cost_reduction_ratio": ratio,
        "final_state": x_final.tolist(),
        "terminal_value_from_P0": float(x0.T @ p_seq[0] @ x0),
        "trace_file": str(TRACE_FILE),
        "primary_output_file": str(REPORT_FILE),
    }

    with open(TRACE_FILE, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
INNERPY
