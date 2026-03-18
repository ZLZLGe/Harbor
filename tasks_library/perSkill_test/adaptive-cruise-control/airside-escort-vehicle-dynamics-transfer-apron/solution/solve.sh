#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"

cat <<'PYTHON' > "${ROOT_DIR}/escort_simulation.py"
import csv
import os
from pathlib import Path

import yaml


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))


def load_config():
    with (ROOT_DIR / "apron_escort_config.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


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
    raise ValueError(f"No active segment at t={current_time}")


def simulate():
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

    with (ROOT_DIR / "apron_escort_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    simulate()
PYTHON

python3 "${ROOT_DIR}/escort_simulation.py"
