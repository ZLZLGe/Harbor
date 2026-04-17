#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"

python3 - << 'PY'
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
CASE_FILE = ROOT / "similar_mpc_case.json"
TRACE_FILE = ROOT / "similar_horizon_trace.json"
REPORT_FILE = ROOT / "similar_horizon_report.json"


def load_case():
    with CASE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def ref_at(schedule, k):
    ref = np.array(schedule[0]["ref"], dtype=float)
    for block in schedule:
        if k >= int(block["start"]):
            ref = np.array(block["ref"], dtype=float)
        else:
            break
    return ref


def finite_horizon_gain(A, B, Q, R, Qf, horizon):
    P = Qf.copy()
    K0 = np.zeros((B.shape[1], A.shape[0]), dtype=float)
    for _ in range(int(horizon)):
        S = R + B.T @ P @ B
        K = np.linalg.solve(S, B.T @ P @ A)
        P = Q + A.T @ P @ (A - B @ K)
        K0 = K
    return K0


def settling_fraction(primary_err, switch_step, tol):
    steps = primary_err.shape[0]
    settling_step = steps
    for k in range(switch_step, steps):
        window = primary_err[k:]
        if np.all(window <= tol):
            settling_step = k
            break
    return float(settling_step) / float(steps)


def evaluate_candidate(case, c):
    A = np.array(case["A"], dtype=float)
    B = np.array(case["B"], dtype=float)
    x = np.array(case["x0"], dtype=float)
    d = np.array(case["disturbance"], dtype=float)
    u_bias = np.array(case["u_bias"], dtype=float)
    u_limit = np.array(case["u_limit"], dtype=float)
    primary_idx = np.array(case["primary_indices"], dtype=int)
    secondary_idx = np.array(case["secondary_indices"], dtype=int)

    n = A.shape[0]
    m = B.shape[1]
    q_diag = np.zeros(n, dtype=float)
    q_diag[primary_idx] = float(c["q_primary"])
    q_diag[secondary_idx] = float(c["q_secondary"])
    Q = np.diag(q_diag)
    R = float(c["r_scale"]) * np.eye(m)
    Qf = float(case["terminal_weight_scale"]) * Q

    K = finite_horizon_gain(A, B, Q, R, Qf, int(c["horizon"]))

    records = []
    states = []
    refs = []
    controls = []

    for k in range(int(case["steps"])):
        ref = ref_at(case["reference_schedule"], k)
        u = u_bias - K @ (x - ref)
        u = np.clip(u, -u_limit, u_limit)

        records.append(
            {
                "k": int(k),
                "reference": [float(v) for v in ref.tolist()],
                "state": [float(v) for v in x.tolist()],
                "control": [float(v) for v in u.tolist()]
            }
        )
        states.append(x.copy())
        refs.append(ref.copy())
        controls.append(u.copy())

        x = A @ x + B @ u + d

    states = np.array(states, dtype=float)
    refs = np.array(refs, dtype=float)
    controls = np.array(controls, dtype=float)

    err_primary = np.abs(states[:, primary_idx] - refs[:, primary_idx])
    tracking_rmse = float(np.sqrt(np.mean((states - refs) ** 2)))
    control_rms = float(np.sqrt(np.mean(controls ** 2)))
    overshoot_primary = float(np.max(np.maximum(states[:, primary_idx] - refs[:, primary_idx], 0.0)))

    switch_step = int(case["reference_schedule"][1]["start"])
    sf = settling_fraction(err_primary, switch_step, float(case["settling_tol"]))

    w = case["weights"]
    score = (
        float(w["tracking_rmse"]) * tracking_rmse
        + float(w["control_rms"]) * control_rms
        + float(w["overshoot_primary"]) * overshoot_primary
        + float(w["settling_fraction"]) * sf
    )

    summary = {
        "candidate_id": c["id"],
        "horizon": int(c["horizon"]),
        "tracking_rmse": tracking_rmse,
        "control_rms": control_rms,
        "overshoot_primary": overshoot_primary,
        "settling_fraction": sf,
        "score": float(score)
    }
    return summary, records


def main():
    case = load_case()
    ranked = []
    traces = {}
    for c in case["candidates"]:
        summary, records = evaluate_candidate(case, c)
        ranked.append(summary)
        traces[c["id"]] = records

    ranked.sort(key=lambda row: (row["score"], row["horizon"], row["candidate_id"]))
    best = ranked[0]

    trace = {
        "scenario": case["scenario"],
        "selected_candidate_id": best["candidate_id"],
        "records": traces[best["candidate_id"]]
    }
    report = {
        "scenario": case["scenario"],
        "best_candidate_id": best["candidate_id"],
        "best_horizon": best["horizon"],
        "ranking": ranked,
        "weights": case["weights"],
        "trace_file": "/root/similar_horizon_trace.json"
    }

    with TRACE_FILE.open("w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)
    with REPORT_FILE.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
PY

echo "Wrote ${ROOT_DIR}/similar_horizon_trace.json and ${ROOT_DIR}/similar_horizon_report.json"
