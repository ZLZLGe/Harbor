import csv
import os
from pathlib import Path

import pandas as pd
import yaml


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
CONFIG_PATH = ROOT_DIR / "apron_escort_config.yaml"
SCRIPT_PATH = ROOT_DIR / "escort_simulation.py"
OUTPUT_PATH = ROOT_DIR / "apron_escort_timeline.csv"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def format_float(value):
    return f"{value:.3f}"


def interpolate_speed(points, target_time):
    if target_time <= float(points[0]["time"]):
        return float(points[0]["speed"])
    if target_time >= float(points[-1]["time"]):
        return float(points[-1]["speed"])

    for left, right in zip(points, points[1:]):
        left_time = float(left["time"])
        right_time = float(right["time"])
        if left_time <= target_time <= right_time:
            span = right_time - left_time
            if span == 0.0:
                return float(right["speed"])
            ratio = (target_time - left_time) / span
            left_speed = float(left["speed"])
            right_speed = float(right["speed"])
            return left_speed + ratio * (right_speed - left_speed)

    return float(points[-1]["speed"])


def integrate_profile(points, start_time, end_time):
    if end_time <= start_time:
        return 0.0

    distance = 0.0
    for left, right in zip(points, points[1:]):
        left_time = float(left["time"])
        right_time = float(right["time"])
        seg_start = max(start_time, left_time)
        seg_end = min(end_time, right_time)
        if seg_end <= seg_start:
            continue
        start_speed = interpolate_speed(points, seg_start)
        end_speed = interpolate_speed(points, seg_end)
        distance += 0.5 * (start_speed + end_speed) * (seg_end - seg_start)
    return distance


def build_segment_offsets(segments, initial_gap):
    offsets = {}
    current_position = float(initial_gap)
    for segment in segments:
        offsets[segment["name"]] = current_position
        current_position += integrate_profile(
            segment["speed_profile"],
            float(segment["start"]),
            float(segment["end"]),
        )
    return offsets


def active_segment(segments, current_time):
    for segment in segments:
        if float(segment["start"]) <= current_time <= float(segment["end"]):
            return segment
    raise AssertionError(f"No active segment at t={current_time}")


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


def build_oracle_rows():
    config = load_config()
    dt = float(config["simulation"]["dt"])
    duration = float(config["simulation"]["duration"])
    control = config["control"]
    segments = config["lead_vehicle"]["segments"]
    offsets = build_segment_offsets(segments, config["lead_vehicle"]["initial_gap"])

    ego_speed = float(config["ego"]["initial_speed"])
    ego_position = float(config["ego"]["initial_position"])
    rows = []

    total_steps = int(round(duration / dt))
    for step in range(total_steps + 1):
        current_time = round(step * dt, 10)
        segment = active_segment(segments, current_time)
        lead_speed = interpolate_speed(segment["speed_profile"], current_time)
        lead_position = offsets[segment["name"]] + integrate_profile(
            segment["speed_profile"],
            float(segment["start"]),
            current_time,
        )
        gap = lead_position - ego_position
        safe_gap = float(control["min_gap"]) + float(control["time_headway"]) * ego_speed
        relative_speed = ego_speed - lead_speed
        ttc = None
        if relative_speed > 0.0 and gap > 0.0:
            ttc = gap / relative_speed

        if gap < float(control["min_gap"]):
            mode = "emergency"
            accel_cmd = float(control["max_decel"])
        elif ttc is not None and ttc < float(control["ttc_threshold"]):
            mode = "emergency"
            accel_cmd = float(control["max_decel"])
        elif gap <= safe_gap + float(control["release_gap"]):
            mode = "escort"
            accel_cmd = clamp(
                float(control["gap_gain"]) * (gap - safe_gap)
                + float(control["relative_gain"]) * (lead_speed - ego_speed),
                float(control["max_decel"]),
                float(control["max_accel"]),
            )
        else:
            mode = "approach"
            target_speed = min(float(control["target_speed"]), float(segment["speed_limit"]))
            accel_cmd = clamp(
                float(control["approach_gain"]) * (target_speed - ego_speed),
                float(control["max_decel"]),
                float(control["max_accel"]),
            )

        rows.append(
            {
                "time": format_float(current_time),
                "zone": segment["zone"],
                "speed_limit": format_float(float(segment["speed_limit"])),
                "lead_speed": format_float(lead_speed),
                "lead_position": format_float(lead_position),
                "ego_speed": format_float(ego_speed),
                "ego_position": format_float(ego_position),
                "gap": format_float(gap),
                "safe_gap": format_float(safe_gap),
                "ttc": "" if ttc is None else format_float(ttc),
                "mode": mode,
                "accel_cmd": format_float(accel_cmd),
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_position = ego_position + ego_speed * dt

    return rows


def test_required_files_exist():
    assert CONFIG_PATH.exists(), "apron_escort_config.yaml is missing"
    assert SCRIPT_PATH.exists(), "escort_simulation.py is missing"
    assert OUTPUT_PATH.exists(), "apron_escort_timeline.csv is missing"


def test_input_config_integrity():
    config = load_config()
    assert config["simulation"]["dt"] == 0.5
    assert config["simulation"]["duration"] == 80.0
    assert config["control"]["min_gap"] == 11.0
    assert config["control"]["ttc_threshold"] == 3.6
    assert len(config["lead_vehicle"]["segments"]) == 6
    assert config["lead_vehicle"]["segments"][-1]["zone"] == "hazard_stop"


def test_output_format():
    trace = pd.read_csv(OUTPUT_PATH, dtype=str, keep_default_na=False)
    assert list(trace.columns) == [
        "time",
        "zone",
        "speed_limit",
        "lead_speed",
        "lead_position",
        "ego_speed",
        "ego_position",
        "gap",
        "safe_gap",
        "ttc",
        "mode",
        "accel_cmd",
    ]
    assert len(trace) == 161
    assert trace.iloc[0]["time"] == "0.000"
    assert trace.iloc[-1]["time"] == "80.000"


def test_output_matches_oracle():
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        actual_rows = list(csv.DictReader(handle))
    assert actual_rows == build_oracle_rows()


def test_modes_and_safety():
    trace = pd.read_csv(OUTPUT_PATH)
    assert set(trace["mode"].unique()) == {"approach", "escort", "emergency"}
    assert trace["ego_speed"].min() >= 0.0
    assert trace["accel_cmd"].max() <= 2.4 + 1e-9
    assert trace["accel_cmd"].min() >= -5.0 - 1e-9
    assert trace["gap"].min() > 11.0

    emergency = trace[trace["mode"] == "emergency"]
    assert list(emergency["time"].round(3)) == [50.0, 50.5]
    assert (emergency["accel_cmd"] == -5.0).all()


def test_zone_behaviour():
    trace = pd.read_csv(OUTPUT_PATH, dtype=str, keep_default_na=False)

    stand_window = trace[(trace["time"].astype(float) >= 50.0) & (trace["time"].astype(float) <= 57.0)]
    assert set(stand_window["zone"]) == {"stand_stop"}

    hazard_window = trace[trace["zone"] == "hazard_stop"]
    assert hazard_window.iloc[0]["time"] == "65.500"
    assert hazard_window.iloc[-1]["time"] == "80.000"

    blank_ttc = trace[trace["ttc"] == ""]
    assert len(blank_ttc) > 0
