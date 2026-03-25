#!/usr/bin/env python3

import csv
import json
import statistics


OUTPUT_PATH = "/root/spinup_trace.csv"
PROFILE_PATH = "/root/fan_bench_profile.json"
TRUTH_PATH = "/tests/reference_truth.json"


def load_profile():
    with open(PROFILE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_truth():
    with open(TRUTH_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_rows():
    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames


def to_float_rows(rows):
    converted = []
    for row in rows:
        converted.append(
            {
                "time_s": float(row["time_s"]),
                "drive_voltage_v": float(row["drive_voltage_v"]),
                "measured_rpm": float(row["measured_rpm"]),
            }
        )
    return converted


def moving_average(values, radius=2):
    smoothed = []
    for index in range(len(values)):
        start = max(0, index - radius)
        stop = min(len(values), index + radius + 1)
        window = values[start:stop]
        smoothed.append(sum(window) / len(window))
    return smoothed


def get_step_start_index(rows):
    for index, row in enumerate(rows):
        if row["drive_voltage_v"] > 0.0:
            return index
    raise AssertionError("轨迹中没有正向电压阶跃")


def compute_tau(rows, step_start_index, baseline_rpm, tail_rpm):
    target_rpm = baseline_rpm + 0.632 * (tail_rpm - baseline_rpm)
    smoothed = moving_average([row["measured_rpm"] for row in rows[step_start_index:]])
    for offset, value in enumerate(smoothed):
        if value >= target_rpm:
            return rows[step_start_index + offset]["time_s"] - rows[step_start_index]["time_s"]
    raise AssertionError("轨迹没有在保持段内达到 63.2% 响应点")


def test_csv_header_and_size():
    rows, fieldnames = load_rows()

    assert fieldnames == ["time_s", "drive_voltage_v", "measured_rpm"]
    assert len(rows) >= 180, "数据行数不足 180"


def test_single_step_contract():
    profile = load_profile()
    rows, _ = load_rows()
    rows = to_float_rows(rows)

    assert rows[0]["time_s"] == 0.0, "首个时间戳必须为 0"

    intervals = [
        rows[index + 1]["time_s"] - rows[index]["time_s"]
        for index in range(len(rows) - 1)
    ]
    assert all(delta > 0 for delta in intervals), "时间戳必须严格递增"
    mean_interval = statistics.mean(intervals)
    assert abs(mean_interval - profile["sample_period_s"]) <= 1e-6

    step_start_index = get_step_start_index(rows)
    baseline_rows = rows[:step_start_index]
    step_rows = rows[step_start_index:]
    assert baseline_rows, "必须先有基线段"
    assert step_rows, "必须有阶跃保持段"

    assert {round(row["drive_voltage_v"], 6) for row in baseline_rows} == {0.0}

    stepped_voltages = {round(row["drive_voltage_v"], 6) for row in step_rows}
    assert len(stepped_voltages) == 1, "阶跃后必须保持固定电压"
    step_voltage = next(iter(stepped_voltages))
    low, high = profile["recommended_voltage_window_v"]
    assert low <= step_voltage <= high

    baseline_duration_s = step_rows[0]["time_s"] - rows[0]["time_s"]
    hold_duration_s = step_rows[-1]["time_s"] - step_rows[0]["time_s"]
    assert baseline_duration_s >= profile["minimum_baseline_s"]
    assert hold_duration_s >= profile["minimum_hold_s"]


def test_information_content_and_headroom():
    profile = load_profile()
    rows, _ = load_rows()
    rows = to_float_rows(rows)
    step_start_index = get_step_start_index(rows)

    baseline_rows = rows[:step_start_index]
    tail_rows = rows[-20:]

    baseline_rpm = statistics.mean(row["measured_rpm"] for row in baseline_rows)
    tail_rpm = statistics.mean(row["measured_rpm"] for row in tail_rows)

    assert tail_rpm - baseline_rpm >= 1200.0, "转速提升不足 1200 RPM"
    assert max(row["measured_rpm"] for row in rows) < profile["soft_rpm_ceiling_rpm"]


def test_recoverable_first_order_parameters():
    truth = load_truth()
    rows, _ = load_rows()
    rows = to_float_rows(rows)
    step_start_index = get_step_start_index(rows)

    baseline_rows = rows[:step_start_index]
    step_rows = rows[step_start_index:]
    tail_rows = rows[-20:]

    baseline_rpm = statistics.mean(row["measured_rpm"] for row in baseline_rows)
    tail_rpm = statistics.mean(row["measured_rpm"] for row in tail_rows)
    step_voltage = step_rows[0]["drive_voltage_v"]

    estimated_gain = (tail_rpm - baseline_rpm) / step_voltage
    estimated_tau = compute_tau(rows, step_start_index, baseline_rpm, tail_rpm)

    gain_error = abs(estimated_gain - truth["gain_rpm_per_v"]) / truth["gain_rpm_per_v"]
    tau_error = abs(estimated_tau - truth["time_constant_s"]) / truth["time_constant_s"]

    assert gain_error <= 0.12, f"增益误差 {gain_error:.3f} 超过 12%"
    assert tau_error <= 0.15, f"时间常数误差 {tau_error:.3f} 超过 15%"
