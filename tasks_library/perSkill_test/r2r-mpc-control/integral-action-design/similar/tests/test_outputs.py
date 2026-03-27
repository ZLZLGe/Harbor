import json
from pathlib import Path

import numpy as np


CASE_FILE = Path("/root/similar_line_case.json")
TRACE_FILE = Path("/root/similar_tension_trace.json")
REPORT_FILE = Path("/root/similar_tension_offset_report.json")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
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
                "reference": ref,
                "state": x.copy(),
                "u_mpc": u_mpc.copy(),
                "integral": integ.copy(),
                "u_total": u_total.copy(),
            }
        )

        x = alpha * x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records


def tail_mae(records, tail_window):
    arr_state = np.array([row["state"] for row in records], dtype=float)
    arr_ref = np.array([row["reference"] for row in records], dtype=float)
    return float(np.mean(np.abs(arr_state[-tail_window:] - arr_ref[-tail_window:])))


def test_similar_outputs():
    cfg = load_json(CASE_FILE)
    trace = load_json(TRACE_FILE)
    report = load_json(REPORT_FILE)

    assert report["scenario"] == cfg["scenario"]
    assert report["trace_file"] == "/root/similar_tension_trace.json"

    records = trace["records"]
    assert len(records) == int(cfg["steps"])

    expected_baseline = simulate(cfg, use_integral=False)
    expected_controlled = simulate(cfg, use_integral=True)

    submitted_state = np.array([row["state"] for row in records], dtype=float)
    submitted_ref = np.array([row["reference"] for row in records], dtype=float)
    submitted_u_mpc = np.array([row["u_mpc"] for row in records], dtype=float)
    submitted_integ = np.array([row["integral"] for row in records], dtype=float)
    submitted_u_total = np.array([row["u_total"] for row in records], dtype=float)

    expected_state = np.array([row["state"] for row in expected_controlled], dtype=float)
    expected_ref = np.array([row["reference"] for row in expected_controlled], dtype=float)
    expected_u_mpc = np.array([row["u_mpc"] for row in expected_controlled], dtype=float)
    expected_integ = np.array([row["integral"] for row in expected_controlled], dtype=float)
    expected_u_total = np.array([row["u_total"] for row in expected_controlled], dtype=float)

    assert np.allclose(submitted_state, expected_state, atol=1e-8)
    assert np.allclose(submitted_ref, expected_ref, atol=1e-8)
    assert np.allclose(submitted_u_mpc, expected_u_mpc, atol=1e-8)
    assert np.allclose(submitted_integ, expected_integ, atol=1e-8)
    assert np.allclose(submitted_u_total, expected_u_total, atol=1e-8)

    max_integral = np.array(cfg["max_integral"], dtype=float)
    assert np.all(np.abs(submitted_integ) <= max_integral + 1e-9)

    tail_window = int(cfg["tail_window"])
    baseline_tail = tail_mae(expected_baseline, tail_window)
    controlled_tail = tail_mae(expected_controlled, tail_window)
    improvement = 1.0 - controlled_tail / baseline_tail
    max_abs_integral = float(np.max(np.abs(expected_integ)))

    kpis = report["kpis"]
    assert np.isclose(float(kpis["baseline_tail_mae"]), baseline_tail, atol=1e-10)
    assert np.isclose(float(kpis["controlled_tail_mae"]), controlled_tail, atol=1e-10)
    assert np.isclose(float(kpis["improvement_ratio"]), improvement, atol=1e-10)
    assert np.isclose(float(kpis["max_abs_integral"]), max_abs_integral, atol=1e-10)

    assert np.allclose(np.array(report["final_state"], dtype=float), expected_state[-1], atol=1e-8)
    assert np.allclose(np.array(report["final_reference"], dtype=float), expected_ref[-1], atol=1e-8)

    # Performance contract: corrected controller must materially reduce tail error.
    assert controlled_tail < 0.75 * baseline_tail
