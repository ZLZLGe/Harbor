import csv
import os
from pathlib import Path

import yaml


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
TRACE_PATH = ROOT_DIR / "tugger_gap_log.csv"
SCRIPT_PATH = ROOT_DIR / "tugger_convoy_sim.py"
CONFIG_PATH = ROOT_DIR / "warehouse_tugger_config.yaml"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def round_str(value):
    return f"{value:.3f}"


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


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


def build_oracle_rows():
    config = load_config()
    dt = float(config["simulation"]["dt"])
    duration = float(config["simulation"]["duration"])
    controller = config["controller"]
    segments = config["lead_segments"]

    ego_speed = float(config["ego"]["initial_speed"])
    ego_position = float(config["ego"]["initial_position"])
    total_steps = int(round(duration / dt))
    segment_start_positions = {}
    rows = []

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

    return rows


def load_actual_rows():
    with TRACE_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check_required_files():
    assert CONFIG_PATH.exists(), "warehouse_tugger_config.yaml is missing"
    assert SCRIPT_PATH.exists(), "tugger_convoy_sim.py is missing"
    assert TRACE_PATH.exists(), "tugger_gap_log.csv is missing"


def check_trace_format():
    rows = load_actual_rows()
    expected_columns = [
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
    ]

    assert rows, "tugger_gap_log.csv is empty"
    assert list(rows[0].keys()) == expected_columns

    config = load_config()
    dt = float(config["simulation"]["dt"])
    duration = float(config["simulation"]["duration"])
    expected_rows = int(round(duration / dt)) + 1
    assert len(rows) == expected_rows
    assert rows[0]["time"] == "0.000"
    assert rows[-1]["time"] == round_str(duration)

    for row in rows:
        assert row["lead_present"] in {"0", "1"}
        assert row["mode"] in {"cruise", "follow", "emergency"}


def check_trace_matches_oracle():
    actual_rows = load_actual_rows()
    expected_rows = build_oracle_rows()
    assert actual_rows == expected_rows


def check_modes_and_safety_windows():
    rows = load_actual_rows()
    config = load_config()
    controller = config["controller"]

    modes = {row["mode"] for row in rows}
    assert modes == {"cruise", "follow", "emergency"}

    early_rows = [row for row in rows if float(row["time"]) < 8.0]
    assert all(row["lead_present"] == "0" for row in early_rows)
    assert all(row["mode"] == "cruise" for row in early_rows)

    first_stop = [row for row in rows if 22.0 <= float(row["time"]) <= 30.0]
    second_stop = [row for row in rows if 54.0 <= float(row["time"]) <= 62.0]
    assert any(row["mode"] == "emergency" for row in first_stop)
    assert any(row["mode"] == "emergency" for row in second_stop)

    numeric_gaps = [float(row["gap"]) for row in rows if row["gap"]]
    assert min(numeric_gaps) > 2.5

    accel_values = [float(row["accel_cmd"]) for row in rows]
    assert max(accel_values) <= float(controller["max_accel"]) + 1e-9
    assert min(accel_values) >= float(controller["max_decel"]) - 1e-9


def main():
    checks = [
        ("required_files", check_required_files),
        ("trace_format", check_trace_format),
        ("oracle_match", check_trace_matches_oracle),
        ("modes_and_safety_windows", check_modes_and_safety_windows),
    ]

    for name, check in checks:
        check()
        print(f"{name}: ok")


if __name__ == "__main__":
    main()
