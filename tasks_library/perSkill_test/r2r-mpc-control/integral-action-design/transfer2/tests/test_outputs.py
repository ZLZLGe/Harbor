import json
from pathlib import Path

import numpy as np


CASE_FILE = Path("/root/transfer2_reservoir_case.json")
TRACE_FILE = Path("/root/transfer2_reservoir_trace.json")
REPORT_FILE = Path("/root/transfer2_reservoir_stability.json")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
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
                "reference": ref,
                "level": x.copy(),
                "u_nominal": u_nominal.copy(),
                "integral": integ.copy(),
                "u_total": u_total.copy(),
            }
        )

        x = alpha * x + coupling @ x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records


def tail_rmse(records, tail_window):
    level = np.array([row["level"] for row in records], dtype=float)
    ref = np.array([row["reference"] for row in records], dtype=float)
    err = level[-tail_window:] - ref[-tail_window:]
    return float(np.sqrt(np.mean(err * err)))


def test_transfer2_outputs():
    cfg = load_json(CASE_FILE)
    trace = load_json(TRACE_FILE)
    report = load_json(REPORT_FILE)

    records = trace["records"]
    assert len(records) == int(cfg["steps"])
    assert report["scenario"] == cfg["scenario"]
    assert report["trace_file"] == "/root/transfer2_reservoir_trace.json"

    expected_baseline = simulate(cfg, use_integral=False)
    expected_controlled = simulate(cfg, use_integral=True)

    expected_level = np.array([row["level"] for row in expected_controlled], dtype=float)
    expected_ref = np.array([row["reference"] for row in expected_controlled], dtype=float)
    expected_nominal = np.array([row["u_nominal"] for row in expected_controlled], dtype=float)
    expected_integral = np.array([row["integral"] for row in expected_controlled], dtype=float)
    expected_total = np.array([row["u_total"] for row in expected_controlled], dtype=float)

    submitted_level = np.array([row["level"] for row in records], dtype=float)
    submitted_ref = np.array([row["reference"] for row in records], dtype=float)
    submitted_nominal = np.array([row["u_nominal"] for row in records], dtype=float)
    submitted_integral = np.array([row["integral"] for row in records], dtype=float)
    submitted_total = np.array([row["u_total"] for row in records], dtype=float)

    assert np.allclose(submitted_level, expected_level, atol=1e-8)
    assert np.allclose(submitted_ref, expected_ref, atol=1e-8)
    assert np.allclose(submitted_nominal, expected_nominal, atol=1e-8)
    assert np.allclose(submitted_integral, expected_integral, atol=1e-8)
    assert np.allclose(submitted_total, expected_total, atol=1e-8)

    max_integral = np.array(cfg["max_integral"], dtype=float)
    assert np.all(np.abs(submitted_integral) <= max_integral + 1e-9)

    tail_window = int(cfg["tail_window"])
    baseline_rmse = tail_rmse(expected_baseline, tail_window)
    controlled_rmse = tail_rmse(expected_controlled, tail_window)
    improvement = 1.0 - controlled_rmse / baseline_rmse

    overshoot = np.max(np.abs(expected_level - expected_ref), axis=0)
    integral_energy = float(np.mean(np.sum(expected_integral * expected_integral, axis=1)))

    assert np.isclose(float(report["baseline_tail_rmse"]), baseline_rmse, atol=1e-10)
    assert np.isclose(float(report["controlled_tail_rmse"]), controlled_rmse, atol=1e-10)
    assert np.isclose(float(report["improvement_ratio"]), improvement, atol=1e-10)
    assert np.allclose(np.array(report["overshoot_per_tank"], dtype=float), overshoot, atol=1e-10)
    assert np.isclose(float(report["integral_energy"]), integral_energy, atol=1e-10)

    assert controlled_rmse < 0.82 * baseline_rmse
