#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"

python3 - << 'PY'
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
CASE_FILE = ROOT / "transfer3_winder_case.json"
TRACE_FILE = ROOT / "transfer3_winder_trace.json"
REPORT_FILE = ROOT / "transfer3_winder_tuning_report.json"


def load_case():
    with CASE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def cyclic_ref(case, k):
    idx = (int(k) // int(case["cycle_span"])) % len(case["cycle_pattern"])
    return np.array(case["cycle_pattern"][idx], dtype=float)


def finite_horizon_gain(A, B, Q, R, Qf, horizon):
    P = Qf.copy()
    K0 = np.zeros((B.shape[1], A.shape[0]), dtype=float)
    for _ in range(int(horizon)):
        S = R + B.T @ P @ B
        K = np.linalg.solve(S, B.T @ P @ A)
        P = Q + A.T @ P @ (A - B @ K)
        K0 = K
    return K0


def evaluate_candidate(case, c):
    A = np.array(case["A"], dtype=float)
    B = np.array(case["B"], dtype=float)
    x = np.array(case["x0"], dtype=float)
    d = np.array(case["disturbance"], dtype=float)
    u_bias = np.array(case["u_bias"], dtype=float)
    u_limit = np.array(case["u_limit"], dtype=float)
    primary_idx = np.array(case["primary_indices"], dtype=int)
    secondary_idx = np.array(case["secondary_indices"], dtype=int)

    q_diag = np.zeros(A.shape[0], dtype=float)
    q_diag[primary_idx] = float(c["q_primary"])
    q_diag[secondary_idx] = float(c["q_secondary"])
    Q = np.diag(q_diag)
    R = float(c["r_scale"]) * np.eye(B.shape[1])
    Qf = float(case["terminal_weight_scale"]) * Q

    K = finite_horizon_gain(A, B, Q, R, Qf, int(c["horizon"]))

    records = []
    states = []
    refs = []
    controls = []

    for k in range(int(case["steps"])):
        ref = cyclic_ref(case, k)
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

    tracking_rmse = float(np.sqrt(np.mean((states - refs) ** 2)))
    control_rms = float(np.sqrt(np.mean(controls ** 2)))
    control_delta = np.diff(controls, axis=0)
    control_delta_rms = float(np.sqrt(np.mean(control_delta ** 2))) if len(control_delta) > 0 else 0.0

    tail_steps = int(case["tail_steps"])
    primary_err = np.abs(states[:, primary_idx] - refs[:, primary_idx])
    cycle_tail_mae = float(np.mean(primary_err[-tail_steps:]))

    w = case["weights"]
    score = (
        float(w["tracking_rmse"]) * tracking_rmse
        + float(w["control_rms"]) * control_rms
        + float(w["control_delta_rms"]) * control_delta_rms
        + float(w["cycle_tail_mae"]) * cycle_tail_mae
    )

    return {
        "candidate_id": c["id"],
        "horizon": int(c["horizon"]),
        "tracking_rmse": tracking_rmse,
        "control_rms": control_rms,
        "control_delta_rms": control_delta_rms,
        "cycle_tail_mae": cycle_tail_mae,
        "score": float(score)
    }, records


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
        "trace_file": "/root/transfer3_winder_trace.json"
    }

    with TRACE_FILE.open("w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)
    with REPORT_FILE.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
PY

echo "Wrote ${ROOT_DIR}/transfer3_winder_trace.json and ${ROOT_DIR}/transfer3_winder_tuning_report.json"
