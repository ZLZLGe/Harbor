import json
from pathlib import Path

import numpy as np


CASE_FILE = Path("/root/transfer1_oven_case.json")
TIMELINE_FILE = Path("/root/transfer1_oven_timeline.json")
REPORT_FILE = Path("/root/transfer1_oven_balance_report.json")


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
                "reference": ref,
                "temperature": x.copy(),
                "u_nominal": u_nominal.copy(),
                "integral": integ.copy(),
                "u_total": u_total.copy(),
            }
        )

        x = alpha * x + beta * u_total + (1.0 - alpha) * ref + disturbance

    return records, clip_count


def tail_mae(records, tail_window):
    temp = np.array([row["temperature"] for row in records], dtype=float)
    ref = np.array([row["reference"] for row in records], dtype=float)
    return float(np.mean(np.abs(temp[-tail_window:] - ref[-tail_window:])))


def test_transfer1_outputs():
    cfg = load_json(CASE_FILE)
    timeline = load_json(TIMELINE_FILE)
    report = load_json(REPORT_FILE)

    records = timeline["records"]
    assert len(records) == int(cfg["steps"])
    assert report["scenario"] == cfg["scenario"]
    assert report["timeline_file"] == "/root/transfer1_oven_timeline.json"

    expected_baseline, _ = simulate(cfg, use_integral=False)
    expected_controlled, expected_clip_count = simulate(cfg, use_integral=True)

    expected_temp = np.array([row["temperature"] for row in expected_controlled], dtype=float)
    expected_ref = np.array([row["reference"] for row in expected_controlled], dtype=float)
    expected_nominal = np.array([row["u_nominal"] for row in expected_controlled], dtype=float)
    expected_integral = np.array([row["integral"] for row in expected_controlled], dtype=float)
    expected_total = np.array([row["u_total"] for row in expected_controlled], dtype=float)

    submitted_temp = np.array([row["temperature"] for row in records], dtype=float)
    submitted_ref = np.array([row["reference"] for row in records], dtype=float)
    submitted_nominal = np.array([row["u_nominal"] for row in records], dtype=float)
    submitted_integral = np.array([row["integral"] for row in records], dtype=float)
    submitted_total = np.array([row["u_total"] for row in records], dtype=float)

    assert np.allclose(submitted_temp, expected_temp, atol=1e-8)
    assert np.allclose(submitted_ref, expected_ref, atol=1e-8)
    assert np.allclose(submitted_nominal, expected_nominal, atol=1e-8)
    assert np.allclose(submitted_integral, expected_integral, atol=1e-8)
    assert np.allclose(submitted_total, expected_total, atol=1e-8)

    max_integral = np.array(cfg["max_integral"], dtype=float)
    assert np.all(np.abs(submitted_integral) <= max_integral + 1e-9)

    tail_window = int(cfg["tail_window"])
    baseline_tail = tail_mae(expected_baseline, tail_window)
    controlled_tail = tail_mae(expected_controlled, tail_window)
    improvement = 1.0 - controlled_tail / baseline_tail
    zone_peak = np.max(np.abs(expected_temp - expected_ref), axis=0)

    assert np.isclose(float(report["tail_mae_baseline"]), baseline_tail, atol=1e-10)
    assert np.isclose(float(report["tail_mae_controlled"]), controlled_tail, atol=1e-10)
    assert np.isclose(float(report["improvement_ratio"]), improvement, atol=1e-10)
    assert np.allclose(np.array(report["zone_peak_deviation"], dtype=float), zone_peak, atol=1e-10)
    assert int(report["integral_clip_count"]) == int(expected_clip_count)

    # Controlled case must be meaningfully better than baseline.
    assert controlled_tail < 0.8 * baseline_tail
