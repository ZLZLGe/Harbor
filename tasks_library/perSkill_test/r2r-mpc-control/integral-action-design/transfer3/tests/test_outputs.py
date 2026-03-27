import json
import math
from pathlib import Path

import numpy as np


CASE_FILE = Path("/root/transfer3_winder_case.json")
TRACE_FILE = Path("/root/transfer3_winder_trace.json")
REPORT_FILE = Path("/root/transfer3_winder_quality.json")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
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
                "reference": ref,
                "state": x.copy(),
                "u_nominal": u_nominal.copy(),
                "integral": integ.copy(),
                "u_total": u_total.copy(),
            }
        )

        x = alpha * x + coupling @ x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records, sat_hits / steps


def cycle_mae(records, tail_window):
    state = np.array([row["state"] for row in records], dtype=float)
    ref = np.array([row["reference"] for row in records], dtype=float)
    return float(np.mean(np.abs(state[-tail_window:] - ref[-tail_window:])))


def test_transfer3_outputs():
    cfg = load_json(CASE_FILE)
    trace = load_json(TRACE_FILE)
    report = load_json(REPORT_FILE)

    records = trace["records"]
    assert len(records) == int(cfg["steps"])
    assert report["scenario"] == cfg["scenario"]
    assert report["trace_file"] == "/root/transfer3_winder_trace.json"

    expected_baseline, _ = simulate(cfg, use_integral=False)
    expected_controlled, expected_sat_fraction = simulate(cfg, use_integral=True)

    expected_state = np.array([row["state"] for row in expected_controlled], dtype=float)
    expected_ref = np.array([row["reference"] for row in expected_controlled], dtype=float)
    expected_nominal = np.array([row["u_nominal"] for row in expected_controlled], dtype=float)
    expected_integral = np.array([row["integral"] for row in expected_controlled], dtype=float)
    expected_total = np.array([row["u_total"] for row in expected_controlled], dtype=float)

    submitted_state = np.array([row["state"] for row in records], dtype=float)
    submitted_ref = np.array([row["reference"] for row in records], dtype=float)
    submitted_nominal = np.array([row["u_nominal"] for row in records], dtype=float)
    submitted_integral = np.array([row["integral"] for row in records], dtype=float)
    submitted_total = np.array([row["u_total"] for row in records], dtype=float)

    assert np.allclose(submitted_state, expected_state, atol=1e-8)
    assert np.allclose(submitted_ref, expected_ref, atol=1e-8)
    assert np.allclose(submitted_nominal, expected_nominal, atol=1e-8)
    assert np.allclose(submitted_integral, expected_integral, atol=1e-8)
    assert np.allclose(submitted_total, expected_total, atol=1e-8)

    max_integral = np.array(cfg["max_integral"], dtype=float)
    assert np.all(np.abs(submitted_integral) <= max_integral + 1e-9)

    tail_window = int(cfg["tail_window"])
    baseline_mae = cycle_mae(expected_baseline, tail_window)
    controlled_mae = cycle_mae(expected_controlled, tail_window)
    improvement = 1.0 - controlled_mae / baseline_mae
    control_effort_l1 = float(np.sum(np.abs(expected_total)))

    assert np.isclose(float(report["baseline_cycle_mae"]), baseline_mae, atol=1e-10)
    assert np.isclose(float(report["controlled_cycle_mae"]), controlled_mae, atol=1e-10)
    assert np.isclose(float(report["improvement_ratio"]), improvement, atol=1e-10)
    assert np.isclose(float(report["control_effort_l1"]), control_effort_l1, atol=1e-10)
    assert np.isclose(
        float(report["integral_saturation_fraction"]),
        float(expected_sat_fraction),
        atol=1e-12,
    )

    assert controlled_mae < 0.85 * baseline_mae
