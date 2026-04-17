import json
from pathlib import Path
import numpy as np

CASE_FILE = Path("/root/similar_case.json")
TRACE_FILE = Path("/root/similar_lqr_rollout_trace.json")
REPORT_FILE = Path("/root/similar_lqr_audit_report.json")


def load_json(path: Path):
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
        records.append({"k": int(k), "x": x.copy(), "u": u.copy(), "stage_cost": stage_cost})
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


def test_outputs():
    case = load_json(CASE_FILE)
    trace = load_json(TRACE_FILE)
    report = load_json(REPORT_FILE)

    A = np.array(case["A"], dtype=float)
    B = np.array(case["B"], dtype=float)
    Q = np.diag(np.array(case["Q_diag"], dtype=float))
    R = np.diag(np.array(case["R_diag"], dtype=float))
    x0 = np.array(case["x0"], dtype=float)
    horizon = int(case["horizon_N"])
    steps = int(case["rollout_steps"])

    gains, p_seq = backward_riccati(A, B, Q, R, horizon)
    expected_records, expected_stage, expected_terminal, expected_xf = rollout(A, B, Q, R, gains, x0, steps)
    baseline_stage, baseline_terminal = rollout_zero(A, Q, x0, steps)

    assert report["scenario"] == case["scenario"]
    assert report["trace_file"] == str(TRACE_FILE)
    assert report["primary_output_file"] == str(REPORT_FILE)
    assert int(report["state_dim"]) == int(A.shape[0])
    assert int(report["control_dim"]) == int(B.shape[1])
    assert int(report["horizon_N"]) == horizon
    assert int(report["rollout_steps"]) == steps

    submitted = trace["records"]
    assert len(submitted) == steps

    sub_x = np.array([row["x"] for row in submitted], dtype=float)
    sub_u = np.array([row["u"] for row in submitted], dtype=float)
    sub_stage = np.array([row["stage_cost"] for row in submitted], dtype=float)

    exp_x = np.array([row["x"] for row in expected_records], dtype=float)
    exp_u = np.array([row["u"] for row in expected_records], dtype=float)
    exp_stage = np.array(expected_stage, dtype=float)

    assert np.allclose(sub_x, exp_x, atol=1e-9)
    assert np.allclose(sub_u, exp_u, atol=1e-9)
    assert np.allclose(sub_stage, exp_stage, atol=1e-9)

    assert np.allclose(np.array(trace["terminal_state"], dtype=float), expected_xf, atol=1e-9)
    assert np.isclose(float(trace["terminal_cost"]), expected_terminal, atol=1e-9)

    optimized_total = float(sum(expected_stage) + expected_terminal)
    baseline_total = float(sum(baseline_stage) + baseline_terminal)
    reduction = float(1.0 - optimized_total / baseline_total)

    assert np.isclose(float(report["optimized_total_cost"]), optimized_total, atol=1e-9)
    assert np.isclose(float(report["baseline_total_cost"]), baseline_total, atol=1e-9)
    assert np.isclose(float(report["cost_reduction_ratio"]), reduction, atol=1e-9)

    exp_norms = np.array([np.linalg.norm(g, ord="fro") for g in gains], dtype=float)
    sub_norms = np.array(report["gain_fro_norms"], dtype=float)
    assert np.allclose(sub_norms, exp_norms, atol=1e-9)

    assert np.allclose(np.array(report["first_control"], dtype=float), exp_u[0], atol=1e-9)
    assert np.allclose(np.array(report["final_state"], dtype=float), expected_xf, atol=1e-9)

    terminal_value = float(x0.T @ p_seq[0] @ x0)
    assert np.isclose(float(report["terminal_value_from_P0"]), terminal_value, atol=1e-9)

    assert reduction > 0.10
