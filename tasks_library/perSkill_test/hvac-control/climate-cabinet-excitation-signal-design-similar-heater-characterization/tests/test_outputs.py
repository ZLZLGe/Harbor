#!/usr/bin/env python3

import json
import statistics


OUTPUT_PATH = "/root/chamber_characterization.json"
TRUTH_PATH = "/tests/reference_truth.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_step_start_index(samples):
    for index, sample in enumerate(samples):
        if float(sample["heater_percent"]) > 0.0:
            return index
    raise AssertionError("response_segment 中没有正向加热阶跃")


def compute_intervals(samples):
    return [
        float(samples[index + 1]["time_s"]) - float(samples[index]["time_s"])
        for index in range(len(samples) - 1)
    ]


def compute_errors(identified_model, truth):
    gain_error = abs(float(identified_model["gain_c_per_percent"]) - truth["gain_c_per_percent"]) / truth["gain_c_per_percent"]
    tau_error = abs(float(identified_model["time_constant_s"]) - truth["time_constant_s"]) / truth["time_constant_s"]
    return gain_error, tau_error


def test_top_level_contract():
    payload = load_json(OUTPUT_PATH)

    assert isinstance(payload, dict)
    for field in ["experiment", "response_segment", "identified_model", "sufficiency_reason"]:
        assert field in payload, f"缺少顶层字段 {field}"


def test_response_segment_shape():
    payload = load_json(OUTPUT_PATH)
    experiment = payload["experiment"]
    samples = payload["response_segment"]

    assert isinstance(samples, list)
    assert len(samples) >= 80, "response_segment 样本数不足 80"

    for sample in samples:
        for field in ["time_s", "temperature_c", "heater_percent"]:
            assert field in sample, f"样本缺少字段 {field}"

    assert float(samples[0]["time_s"]) == 0.0, "首个时间戳必须是 0"

    intervals = compute_intervals(samples)
    assert all(delta > 0 for delta in intervals), "时间戳必须严格递增"
    mean_interval = statistics.mean(intervals)
    assert mean_interval <= 6.0, "采样周期必须不大于 6 秒"
    assert abs(float(experiment["sample_period_s"]) - mean_interval) <= 0.01

    step_start_index = get_step_start_index(samples)
    baseline = samples[:step_start_index]
    stepped = samples[step_start_index:]
    assert baseline, "阶跃前必须有基线样本"
    assert stepped, "阶跃后必须有阶跃样本"

    baseline_powers = {round(float(sample["heater_percent"]), 3) for sample in baseline}
    assert baseline_powers == {0.0}, "基线阶段必须保持 0% 加热"

    stepped_powers = {round(float(sample["heater_percent"]), 3) for sample in stepped}
    assert len(stepped_powers) == 1, "阶跃后必须保持固定功率"
    step_power = next(iter(stepped_powers))
    assert 20.0 <= step_power <= 60.0, "阶跃功率必须在 20 到 60 之间"
    assert abs(float(experiment["step_heater_percent"]) - step_power) <= 0.01

    baseline_duration_s = float(stepped[0]["time_s"]) - float(samples[0]["time_s"])
    step_duration_s = float(stepped[-1]["time_s"]) - float(stepped[0]["time_s"])
    assert baseline_duration_s >= 30.0, "基线时长至少 30 秒"
    assert step_duration_s >= 360.0, "阶跃保持时长至少 360 秒"
    assert abs(float(experiment["baseline_duration_s"]) - baseline_duration_s) <= mean_interval
    assert abs(float(experiment["step_duration_s"]) - step_duration_s) <= mean_interval


def test_signal_is_informative():
    payload = load_json(OUTPUT_PATH)
    samples = payload["response_segment"]
    step_start_index = get_step_start_index(samples)

    baseline_average = statistics.mean(
        float(sample["temperature_c"]) for sample in samples[:step_start_index]
    )
    tail_average = statistics.mean(
        float(sample["temperature_c"]) for sample in samples[-8:]
    )

    assert tail_average - baseline_average >= 3.0, "阶跃引起的温升不足 3.0 摄氏度"


def test_identified_model_accuracy():
    payload = load_json(OUTPUT_PATH)
    truth = load_json(TRUTH_PATH)
    identified_model = payload["identified_model"]

    for field in ["model_type", "gain_c_per_percent", "time_constant_s"]:
        assert field in identified_model, f"identified_model 缺少字段 {field}"

    assert identified_model["model_type"] == "first_order_heating_step"
    assert float(identified_model["gain_c_per_percent"]) > 0.0
    assert float(identified_model["time_constant_s"]) > 0.0

    gain_error, tau_error = compute_errors(identified_model, truth)
    assert gain_error <= 0.15, f"增益误差 {gain_error:.3f} 超过 15%"
    assert tau_error <= 0.20, f"时间常数误差 {tau_error:.3f} 超过 20%"


def test_sufficiency_reason():
    payload = load_json(OUTPUT_PATH)
    reason = payload["sufficiency_reason"]

    assert isinstance(reason, str)
    assert len(reason.strip()) >= 40, "sufficiency_reason 至少 40 个字符"
