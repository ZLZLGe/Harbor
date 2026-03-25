#!/usr/bin/env python3

import importlib.util
import json
import os

import numpy as np


ROOT = os.environ.get("TASK_ROOT", "/root")
REPORT_PATH = os.path.join(ROOT, "coating_response_report.json")
CONFIG_PATH = os.path.join(ROOT, "coating_line_case.json")
SIMULATOR_PATH = os.path.join(ROOT, "coating_line_simulator.py")
CONTROL_LIMIT = 2.0


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_simulator_class():
    spec = importlib.util.spec_from_file_location(
        "coating_line_simulator_under_test", SIMULATOR_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.CoatingLineSimulator


def expected_reference(config, time_value):
    switch_time = float(config["switch_time"])
    ramp = float(config["speed_ramp_duration"])
    alpha = 0.0 if time_value < switch_time else min((time_value - switch_time) / ramp, 1.0)

    pre = np.array(config["pre_ramp"]["reference_state"], dtype=float)
    post = np.array(config["post_ramp"]["reference_state"], dtype=float)

    tensions = pre[:4].copy()
    if time_value >= switch_time:
        tensions[1:3] = post[1:3]
    speeds = pre[4:] + alpha * (post[4:] - pre[4:])
    return tensions, speeds


def recompute_metrics(report, config):
    dt = float(config["dt"])
    duration = float(config["duration"])
    switch_time = float(config["switch_time"])

    trajectory = report["trajectory"]
    times = np.array([entry["time"] for entry in trajectory], dtype=float)
    tensions = np.array([entry["tensions"] for entry in trajectory], dtype=float)
    speeds = np.array([entry["speeds"] for entry in trajectory], dtype=float)
    ref_tensions = np.array([entry["reference_tensions"] for entry in trajectory], dtype=float)
    ref_speeds = np.array([entry["reference_speeds"] for entry in trajectory], dtype=float)
    controls = np.array([entry["control_inputs"] for entry in trajectory], dtype=float)

    steady_mask = times >= duration - 1.0 - 1e-9
    switch_mask = times >= switch_time - 1e-9

    return {
        "steady_state_tension_error": float(
            np.mean(np.abs(tensions[steady_mask] - ref_tensions[steady_mask]))
        ),
        "steady_state_speed_error": float(
            np.mean(np.abs(speeds[steady_mask] - ref_speeds[steady_mask]))
        ),
        "middle_zone_tension_overshoot": float(
            np.max(
                np.maximum(
                    tensions[switch_mask][:, 1:3] - ref_tensions[switch_mask][:, 1:3],
                    0.0,
                )
            )
        ),
        "line_speed_overshoot": float(
            np.max(np.maximum(speeds[switch_mask] - ref_speeds[switch_mask], 0.0))
        ),
        "control_energy": float(np.sum(dt * np.sum(controls * controls, axis=1))),
    }


def replay_trajectory(report):
    simulator_cls = load_simulator_class()
    simulator = simulator_cls(CONFIG_PATH)
    simulator.reset()

    replay_records = []
    for entry in report["trajectory"]:
        state_before = simulator.state.copy()
        reference_state, reference_input = simulator.get_reference()
        control_input = np.array(entry["control_inputs"], dtype=float)
        phase_before = simulator.get_phase()

        next_state = simulator.step(control_input)
        replay_records.append(
            {
                "entry": entry,
                "phase_before": phase_before,
                "phase_after": simulator.get_phase(),
                "state_before": state_before,
                "reference_state": reference_state,
                "reference_input": reference_input,
                "control_input": control_input,
                "next_state": next_state,
                "time_after": float(simulator.time),
            }
        )

    return replay_records


def infer_feedback_gain(replay_records, phase):
    design_rows = []
    outputs = []
    deviations = []

    for record in replay_records:
        if record["phase_before"] != phase:
            continue

        control_input = record["control_input"]
        if np.any(np.isclose(np.abs(control_input), CONTROL_LIMIT, atol=1e-9)):
            continue

        deviation = record["state_before"] - record["reference_state"]
        design_rows.append(np.kron(np.eye(4), deviation))
        outputs.append(record["reference_input"] - control_input)
        deviations.append(deviation)

    assert len(design_rows) >= 8, f"not enough unsaturated samples for {phase}"

    deviation_matrix = np.vstack(deviations)
    assert np.linalg.matrix_rank(deviation_matrix) == 8, f"{phase} state errors are rank deficient"

    design = np.vstack(design_rows)
    targets = np.concatenate(outputs)
    coefficients, _, _, _ = np.linalg.lstsq(design, targets, rcond=None)
    inferred_gain = coefficients.reshape(4, 8)
    fit_error = float(np.max(np.abs(design @ coefficients - targets)))
    return inferred_gain, fit_error


def stage_zero_fro_norm(report, phase):
    for summary in report["phase_gain_summary"]:
        if summary["phase"] != phase:
            continue
        for sample in summary["sampled_stage_gains"]:
            if sample["stage"] == 0:
                return float(sample["fro_norm"])
    raise AssertionError(f"missing stage 0 summary for {phase}")


def test_report_exists():
    assert os.path.exists(REPORT_PATH), "missing /root/coating_response_report.json"


def test_scenario_and_gain_summary():
    report = load_json(REPORT_PATH)
    config = load_json(CONFIG_PATH)

    scenario = report["scenario"]
    assert set(scenario.keys()) == {"dt", "duration", "switch_time"}
    assert abs(scenario["dt"] - config["dt"]) < 1e-9
    assert abs(scenario["duration"] - config["duration"]) < 1e-9
    assert abs(scenario["switch_time"] - config["switch_time"]) < 1e-9

    summaries = report["phase_gain_summary"]
    assert isinstance(summaries, list) and len(summaries) == 2
    seen = {entry["phase"] for entry in summaries}
    assert seen == {"pre_ramp", "post_ramp"}

    for entry in summaries:
        horizon = entry["horizon"]
        assert isinstance(horizon, int)
        assert 6 <= horizon <= 24
        samples = entry["sampled_stage_gains"]
        assert isinstance(samples, list) and len(samples) >= 3
        stages = {sample["stage"] for sample in samples}
        assert 0 in stages
        assert horizon - 1 in stages
        for sample in samples:
            assert isinstance(sample["stage"], int)
            assert 0 <= sample["stage"] < horizon
            assert np.isfinite(sample["fro_norm"])
            assert sample["fro_norm"] > 0.0


def test_trajectory_contract_and_references():
    report = load_json(REPORT_PATH)
    config = load_json(CONFIG_PATH)
    trajectory = report["trajectory"]

    assert isinstance(trajectory, list) and len(trajectory) > 0

    previous_time = -1.0
    for entry in trajectory:
        for key in (
            "time",
            "phase",
            "tensions",
            "speeds",
            "reference_tensions",
            "reference_speeds",
            "control_inputs",
        ):
            assert key in entry, f"missing field {key}"

        assert entry["phase"] in {"pre_ramp", "post_ramp"}
        assert len(entry["tensions"]) == 4
        assert len(entry["speeds"]) == 4
        assert len(entry["reference_tensions"]) == 4
        assert len(entry["reference_speeds"]) == 4
        assert len(entry["control_inputs"]) == 4
        assert entry["time"] > previous_time
        previous_time = entry["time"]

        expected_tensions, expected_speeds = expected_reference(config, entry["time"])
        np.testing.assert_allclose(entry["reference_tensions"], expected_tensions, atol=1e-9)
        np.testing.assert_allclose(entry["reference_speeds"], expected_speeds, atol=1e-9)

    assert trajectory[-1]["time"] >= config["duration"] - 1e-9


def test_trajectory_replays_in_simulator():
    report = load_json(REPORT_PATH)

    for record in replay_trajectory(report):
        entry = record["entry"]
        assert abs(entry["time"] - record["time_after"]) < 1e-9
        assert entry["phase"] == record["phase_after"]
        np.testing.assert_allclose(entry["tensions"], record["next_state"][:4], atol=1e-9)
        np.testing.assert_allclose(entry["speeds"], record["next_state"][4:], atol=1e-9)


def test_controls_follow_phase_feedback_law():
    report = load_json(REPORT_PATH)
    replay_records = replay_trajectory(report)

    for phase in ("pre_ramp", "post_ramp"):
        inferred_gain, fit_error = infer_feedback_gain(replay_records, phase)
        assert fit_error < 1e-6, f"{phase} controls are not consistent with a single feedback gain"

        reported_norm = stage_zero_fro_norm(report, phase)
        inferred_norm = float(np.linalg.norm(inferred_gain, ord="fro"))
        assert abs(reported_norm - inferred_norm) < 5e-2

        for record in replay_records:
            if record["phase_before"] != phase:
                continue

            deviation = record["state_before"] - record["reference_state"]
            predicted_control = record["reference_input"] - inferred_gain @ deviation
            predicted_control = np.clip(predicted_control, -CONTROL_LIMIT, CONTROL_LIMIT)
            np.testing.assert_allclose(
                record["control_input"], predicted_control, atol=1e-6
            )


def test_metrics_match_definitions():
    report = load_json(REPORT_PATH)
    config = load_json(CONFIG_PATH)
    metrics = report["metrics"]

    expected = recompute_metrics(report, config)
    assert set(metrics.keys()) == set(expected.keys())
    for key, value in expected.items():
        assert abs(metrics[key] - value) < 1e-6, f"{key} does not match recomputed value"


def test_public_thresholds():
    report = load_json(REPORT_PATH)
    metrics = report["metrics"]

    assert metrics["steady_state_tension_error"] < 0.22
    assert metrics["steady_state_speed_error"] < 0.07
    assert metrics["middle_zone_tension_overshoot"] < 0.35
    assert metrics["line_speed_overshoot"] < 0.15
    assert metrics["control_energy"] < 6.5
