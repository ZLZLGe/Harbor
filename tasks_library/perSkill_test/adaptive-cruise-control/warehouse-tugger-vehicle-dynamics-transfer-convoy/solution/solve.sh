#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"

cat <<'PYTHON' > "${ROOT_DIR}/tugger_convoy_sim.py"
import csv
import os
from pathlib import Path

import yaml


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))


def load_config():
    with (ROOT_DIR / "warehouse_tugger_config.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


def round_str(value):
    return f"{value:.3f}"


def interpolate_speed(points, target_time):
    if target_time <= points[0]["time"]:
        return float(points[0]["speed"])
    if target_time >= points[-1]["time"]:
        return float(points[-1]["speed"])

    for left, right in zip(points, points[1:]):
        if left["time"] <= target_time <= right["time"]:
            span = right["time"] - left["time"]
            if span == 0:
                return float(right["speed"])
            ratio = (target_time - left["time"]) / span
            return float(left["speed"]) + ratio * (float(right["speed"]) - float(left["speed"]))

    return float(points[-1]["speed"])


def integrate_speed_profile(points, start_time, end_time):
    if end_time <= start_time:
        return 0.0

    distance = 0.0
    for left, right in zip(points, points[1:]):
        seg_start = max(start_time, float(left["time"]))
        seg_end = min(end_time, float(right["time"]))
        if seg_end <= seg_start:
            continue
        start_speed = interpolate_speed(points, seg_start)
        end_speed = interpolate_speed(points, seg_end)
        distance += 0.5 * (start_speed + end_speed) * (seg_end - seg_start)
    return distance


def active_segment(segments, current_time):
    for segment in segments:
        if float(segment["start"]) <= current_time <= float(segment["end"]):
            return segment
    return None


def simulate():
    config = load_config()
    dt = float(config["simulation"]["dt"])
    duration = float(config["simulation"]["duration"])
    controller = config["controller"]
    segments = config["lead_segments"]

    ego_speed = float(config["ego"]["initial_speed"])
    ego_position = float(config["ego"]["initial_position"])

    segment_start_positions = {}
    rows = []
    total_steps = int(round(duration / dt))

    for step in range(total_steps + 1):
        current_time = round(step * dt, 10)

        for segment in segments:
            if abs(current_time - float(segment["start"])) < 1e-9 and segment["name"] not in segment_start_positions:
                segment_start_positions[segment["name"]] = ego_position + float(segment["start_gap"])

        segment = active_segment(segments, current_time)
        lead_present = segment is not None
        lead_speed = None
        lead_position = None
        gap = None

        if lead_present:
            lead_speed = interpolate_speed(segment["speed_points"], current_time)
            lead_position = segment_start_positions[segment["name"]] + integrate_speed_profile(
                segment["speed_points"], float(segment["start"]), current_time
            )
            gap = lead_position - ego_position

        target_gap = ego_speed * float(controller["time_headway"]) + float(controller["min_gap"])
        ttc = None
        mode = "cruise"
        accel_cmd = clamp(
            float(controller["k_cruise"]) * (float(controller["target_speed"]) - ego_speed),
            float(controller["max_decel"]),
            float(controller["max_accel"]),
        )

        if lead_present:
            relative_speed = ego_speed - lead_speed
            if gap < float(controller["min_gap"]):
                mode = "emergency"
                accel_cmd = float(controller["max_decel"])
            else:
                if relative_speed > 0.0 and gap > 0.0:
                    ttc = gap / relative_speed
                if ttc is not None and ttc < float(controller["ttc_threshold"]):
                    mode = "emergency"
                    accel_cmd = float(controller["max_decel"])
                else:
                    mode = "follow"
                    accel_cmd = clamp(
                        float(controller["k_gap"]) * (gap - target_gap)
                        + float(controller["k_rel"]) * (lead_speed - ego_speed),
                        float(controller["max_decel"]),
                        float(controller["max_accel"]),
                    )

        rows.append(
            {
                "time": round_str(current_time),
                "ego_speed": round_str(ego_speed),
                "ego_position": round_str(ego_position),
                "lead_present": "1" if lead_present else "0",
                "lead_speed": "" if lead_speed is None else round_str(lead_speed),
                "lead_position": "" if lead_position is None else round_str(lead_position),
                "gap": "" if gap is None else round_str(gap),
                "target_gap": round_str(target_gap),
                "ttc": "" if ttc is None else round_str(ttc),
                "mode": mode,
                "accel_cmd": round_str(accel_cmd),
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_position = ego_position + ego_speed * dt

    output_path = ROOT_DIR / "tugger_gap_log.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "time",
                "ego_speed",
                "ego_position",
                "lead_present",
                "lead_speed",
                "lead_position",
                "gap",
                "target_gap",
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

python3 "${ROOT_DIR}/tugger_convoy_sim.py"
