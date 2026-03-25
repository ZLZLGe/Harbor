#!/usr/bin/env python3

import json
import statistics


OUTPUT_PATH = "/root/conductivity_bump_report.json"
PROFILE_PATH = "/root/mixing_station_profile.json"
TRUTH_PATH = "/tests/reference_truth.json"
TAIL_WINDOW = 12


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_report():
    return load_json(OUTPUT_PATH)


def load_profile():
    return load_json(PROFILE_PATH)


def load_truth():
    return load_json(TRUTH_PATH)


def trace_intervals(trace):
    return [
        float(trace[index + 1]["time_s"]) - float(trace[index]["time_s"])
        for index in range(len(trace) - 1)
    ]


def get_step_start_index(trace):
    for index, sample in enumerate(trace):
        if float(sample["brine_pump_lpm"]) > 0.0:
            return index
    raise AssertionError("trace 中没有正向投料泵阶跃")


def computed_summary(trace):
    step_start_index = get_step_start_index(trace)
    baseline_samples = trace[:step_start_index]
    tail_samples = trace[-TAIL_WINDOW:]

    baseline_mean = statistics.mean(
        float(sample["conductivity_ms_cm"]) for sample in baseline_samples
    )
    tail_mean = statistics.mean(
        float(sample["conductivity_ms_cm"]) for sample in tail_samples
    )
    return baseline_mean, tail_mean, tail_mean - baseline_mean


def test_top_level_contract():
    report = load_report()

    assert isinstance(report, dict)
    for field in [
        "experiment",
        "trace",
        "response_summary",
        "identified_model",
        "steady_state_assessment",
    ]:
        assert field in report, f"缺少顶层字段 {field}"


def test_trace_contract():
    profile = load_profile()
    report = load_report()
    experiment = report["experiment"]
    trace = report["trace"]

    assert isinstance(trace, list)
    assert len(trace) >= 95, "trace 样本数不足 95"

    for sample in trace:
        for field in ["time_s", "conductivity_ms_cm", "brine_pump_lpm"]:
            assert field in sample, f"样本缺少字段 {field}"

    assert float(trace[0]["time_s"]) == 0.0, "首个时间戳必须为 0"

    intervals = trace_intervals(trace)
    assert all(delta > 0 for delta in intervals), "时间戳必须严格递增"
    mean_interval = statistics.mean(intervals)
    assert abs(mean_interval - float(profile["sample_period_s"])) <= 1e-6
    assert abs(float(experiment["sample_period_s"]) - mean_interval) <= 1e-6

    step_start_index = get_step_start_index(trace)
    baseline_samples = trace[:step_start_index]
    step_samples = trace[step_start_index:]
    assert baseline_samples, "必须先有基线样本"
    assert step_samples, "必须有阶跃保持段"

    assert {round(float(sample["brine_pump_lpm"]), 6) for sample in baseline_samples} == {0.0}

    stepped_commands = {
        round(float(sample["brine_pump_lpm"]), 6) for sample in step_samples
    }
    assert len(stepped_commands) == 1, "阶跃后必须保持固定流量"
    step_pump_lpm = next(iter(stepped_commands))

    low, high = profile["recommended_step_window_lpm"]
    assert low <= step_pump_lpm <= high
    assert abs(float(experiment["baseline_pump_lpm"])) <= 1e-9
    assert abs(float(experiment["step_pump_lpm"]) - step_pump_lpm) <= 1e-6

    baseline_duration_s = float(step_samples[0]["time_s"]) - float(trace[0]["time_s"])
    hold_duration_s = float(step_samples[-1]["time_s"]) - float(step_samples[0]["time_s"])
    assert baseline_duration_s >= float(profile["minimum_baseline_s"])
    assert hold_duration_s >= float(profile["minimum_hold_s"])
    assert abs(float(experiment["baseline_duration_s"]) - baseline_duration_s) <= mean_interval
    assert abs(float(experiment["hold_duration_s"]) - hold_duration_s) <= mean_interval


def test_response_summary_and_headroom():
    profile = load_profile()
    report = load_report()
    trace = report["trace"]
    response_summary = report["response_summary"]

    baseline_mean, tail_mean, observed_change = computed_summary(trace)

    assert abs(float(response_summary["baseline_mean_ms_cm"]) - baseline_mean) <= 0.02
    assert abs(float(response_summary["tail_mean_ms_cm"]) - tail_mean) <= 0.02
    assert abs(float(response_summary["observed_change_ms_cm"]) - observed_change) <= 0.02

    assert observed_change >= 1.8, "响应提升不足 1.8 mS/cm"
    assert observed_change >= 8.0 * float(profile["noise_std_ms_cm"])
    assert max(float(sample["conductivity_ms_cm"]) for sample in trace) < float(
        profile["max_safe_conductivity_ms_cm"]
    )


def test_identified_model_accuracy():
    report = load_report()
    truth = load_truth()
    experiment = report["experiment"]
    response_summary = report["response_summary"]
    identified_model = report["identified_model"]

    for field in [
        "model_type",
        "gain_ms_cm_per_lpm",
        "time_constant_s",
        "predicted_plateau_ms_cm",
    ]:
        assert field in identified_model, f"identified_model 缺少字段 {field}"

    assert identified_model["model_type"] == "first_order_mixing_step"
    assert float(identified_model["gain_ms_cm_per_lpm"]) > 0.0
    assert float(identified_model["time_constant_s"]) > 0.0
    assert float(identified_model["predicted_plateau_ms_cm"]) > 0.0

    predicted_plateau_from_formula = float(response_summary["baseline_mean_ms_cm"]) + (
        float(identified_model["gain_ms_cm_per_lpm"]) * float(experiment["step_pump_lpm"])
    )
    assert abs(
        float(identified_model["predicted_plateau_ms_cm"]) - predicted_plateau_from_formula
    ) <= 0.1

    gain_error = abs(
        float(identified_model["gain_ms_cm_per_lpm"]) - float(truth["gain_ms_cm_per_lpm"])
    ) / float(truth["gain_ms_cm_per_lpm"])
    tau_error = abs(
        float(identified_model["time_constant_s"]) - float(truth["time_constant_s"])
    ) / float(truth["time_constant_s"])

    assert gain_error <= 0.12, f"增益误差 {gain_error:.3f} 超过 12%"
    assert tau_error <= 0.15, f"时间常数误差 {tau_error:.3f} 超过 15%"


def test_steady_state_assessment():
    report = load_report()
    response_summary = report["response_summary"]
    identified_model = report["identified_model"]
    assessment = report["steady_state_assessment"]

    for field in ["near_steady_state", "remaining_gap_ms_cm", "evidence"]:
        assert field in assessment, f"steady_state_assessment 缺少字段 {field}"

    observed_change = float(response_summary["observed_change_ms_cm"])
    tail_mean = float(response_summary["tail_mean_ms_cm"])
    predicted_plateau = float(identified_model["predicted_plateau_ms_cm"])
    expected_gap = max(0.0, predicted_plateau - tail_mean)

    assert abs(float(assessment["remaining_gap_ms_cm"]) - expected_gap) <= 0.08

    expected_flag = (
        expected_gap <= 0.25
        and expected_gap <= 0.12 * observed_change
    )
    assert bool(assessment["near_steady_state"]) is expected_flag

    evidence = assessment["evidence"]
    assert isinstance(evidence, str)
    assert len(evidence.strip()) >= 35
