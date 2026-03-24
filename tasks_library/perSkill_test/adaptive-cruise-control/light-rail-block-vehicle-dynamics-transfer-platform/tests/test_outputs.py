import csv
import os
from pathlib import Path

import pandas as pd
import yaml


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
CONFIG_PATH = ROOT_DIR / "tram_block_config.yaml"
SCRIPT_PATH = ROOT_DIR / "tram_platform_sim.py"
TRACE_PATH = ROOT_DIR / "tram_block_trace.csv"
SUMMARY_PATH = ROOT_DIR / "tram_block_summary.yaml"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


def round_str(value):
    return f"{value:.3f}"


def round_float(value):
    if value is None:
        return None
    return round(float(value), 3)


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


def active_segment(segments, current_time):
    for segment in segments:
        if float(segment["start"]) <= current_time <= float(segment["end"]):
            return segment
    return None


def first_mode_time(rows, mode_name):
    for row in rows:
        if row["mode"] == mode_name:
            return float(row["time"])
    return None


def first_return_to_run(rows, first_emergency_time):
    if first_emergency_time is None:
        return None
    for row in rows:
        current_time = float(row["time"])
        if current_time > first_emergency_time and row["mode"] == "run":
            return current_time
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
            segment_start = float(segment["start"])
            if abs(current_time - segment_start) < 1e-9 and segment["name"] not in segment_start_positions:
                segment_start_positions[segment["name"]] = ego_position + float(segment["start_gap"])

        segment = active_segment(segments, current_time)
        lead_present = segment is not None
        segment_name = ""
        lead_speed = None
        lead_position = None
        gap = None

        if lead_present:
            segment_name = segment["name"]
            lead_speed = interpolate_speed(segment["speed_points"], current_time)
            lead_position = segment_start_positions[segment_name] + integrate_profile(
                segment["speed_points"],
                float(segment["start"]),
                current_time,
            )
            gap = lead_position - ego_position

        protect_gap = float(controller["min_gap"]) + float(controller["time_headway"]) * ego_speed
        ttc = None
        mode = "run"
        accel_cmd = clamp(
            float(controller["k_run"]) * (float(controller["target_speed"]) - ego_speed),
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
                    mode = "spacing"
                    accel_cmd = clamp(
                        float(controller["k_gap"]) * (gap - protect_gap)
                        + float(controller["k_rel"]) * (lead_speed - ego_speed),
                        float(controller["max_decel"]),
                        float(controller["max_accel"]),
                    )

        rows.append(
            {
                "time": round_str(current_time),
                "segment": segment_name,
                "ego_speed": round_str(ego_speed),
                "ego_position": round_str(ego_position),
                "lead_present": "1" if lead_present else "0",
                "lead_speed": "" if lead_speed is None else round_str(lead_speed),
                "lead_position": "" if lead_position is None else round_str(lead_position),
                "gap": "" if gap is None else round_str(gap),
                "protect_gap": round_str(protect_gap),
                "ttc": "" if ttc is None else round_str(ttc),
                "mode": mode,
                "accel_cmd": round_str(accel_cmd),
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_position = ego_position + ego_speed * dt

    return rows


def build_oracle_summary(rows):
    config = load_config()
    lead_rows = [row for row in rows if row["lead_present"] == "1"]
    ttc_values = [float(row["ttc"]) for row in rows if row["ttc"] != ""]
    margins = [float(row["gap"]) - float(row["protect_gap"]) for row in lead_rows]

    first_spacing_time = first_mode_time(rows, "spacing")
    first_emergency_time = first_mode_time(rows, "emergency")
    return_to_run_time = first_return_to_run(rows, first_emergency_time)

    mode_samples = {
        "run": sum(1 for row in rows if row["mode"] == "run"),
        "spacing": sum(1 for row in rows if row["mode"] == "spacing"),
        "emergency": sum(1 for row in rows if row["mode"] == "emergency"),
    }

    min_gap = min(float(row["gap"]) for row in lead_rows)
    min_ttc = min(ttc_values) if ttc_values else None
    min_margin = min(margins)
    final_speed = float(rows[-1]["ego_speed"])
    final_position = float(rows[-1]["ego_position"])
    hard_floor_ok = min_gap >= float(config["summary_rules"]["hard_floor_gap"])
    emergency_observed = mode_samples["emergency"] > 0
    recovered_to_run = return_to_run_time is not None
    all_modes_observed = all(count > 0 for count in mode_samples.values())

    return {
        "scenario": {
            "duration": round_float(config["simulation"]["duration"]),
            "dt": round_float(config["simulation"]["dt"]),
            "target_speed": round_float(config["controller"]["target_speed"]),
            "lead_segments": len(config["lead_segments"]),
        },
        "events": {
            "first_spacing_time": round_float(first_spacing_time),
            "first_emergency_time": round_float(first_emergency_time),
            "return_to_run_time": round_float(return_to_run_time),
        },
        "metrics": {
            "min_gap": round_float(min_gap),
            "min_ttc": round_float(min_ttc),
            "min_margin": round_float(min_margin),
            "mode_samples": mode_samples,
            "final_speed": round_float(final_speed),
            "final_position": round_float(final_position),
        },
        "checks": {
            "hard_floor_ok": hard_floor_ok,
            "emergency_observed": emergency_observed,
            "recovered_to_run": recovered_to_run,
            "all_modes_observed": all_modes_observed,
            "summary_ready": hard_floor_ok and emergency_observed and recovered_to_run and all_modes_observed,
        },
    }


def test_required_files_exist():
    assert CONFIG_PATH.exists(), "tram_block_config.yaml is missing"
    assert SCRIPT_PATH.exists(), "tram_platform_sim.py is missing"
    assert TRACE_PATH.exists(), "tram_block_trace.csv is missing"
    assert SUMMARY_PATH.exists(), "tram_block_summary.yaml is missing"


def test_input_config_integrity():
    config = load_config()
    assert config["simulation"]["dt"] == 0.5
    assert config["simulation"]["duration"] == 72.0
    assert config["controller"]["target_speed"] == 16.0
    assert config["controller"]["min_gap"] == 12.0
    assert config["controller"]["ttc_threshold"] == 4.0
    assert config["summary_rules"]["hard_floor_gap"] == 6.0
    assert len(config["lead_segments"]) == 2
    assert config["lead_segments"][0]["name"] == "platform_stop"
    assert config["lead_segments"][1]["name"] == "short_block"


def test_trace_format():
    trace = pd.read_csv(TRACE_PATH, dtype=str, keep_default_na=False)
    assert list(trace.columns) == [
        "time",
        "segment",
        "ego_speed",
        "ego_position",
        "lead_present",
        "lead_speed",
        "lead_position",
        "gap",
        "protect_gap",
        "ttc",
        "mode",
        "accel_cmd",
    ]
    assert len(trace) == 145
    assert trace.iloc[0]["time"] == "0.000"
    assert trace.iloc[-1]["time"] == "72.000"


def test_trace_matches_oracle():
    with TRACE_PATH.open("r", encoding="utf-8", newline="") as handle:
        actual_rows = list(csv.DictReader(handle))
    assert actual_rows == build_oracle_rows()


def test_summary_matches_oracle():
    with SUMMARY_PATH.open("r", encoding="utf-8") as handle:
        actual_summary = yaml.safe_load(handle)
    assert actual_summary == build_oracle_summary(build_oracle_rows())


def test_modes_and_recovery():
    trace = pd.read_csv(TRACE_PATH)
    assert set(trace["mode"].unique()) == {"run", "spacing", "emergency"}
    assert trace["ego_speed"].min() >= 0.0
    assert trace["accel_cmd"].max() <= 1.3 + 1e-9
    assert trace["accel_cmd"].min() >= -3.6 - 1e-9

    spacing_window = trace[(trace["time"] >= 18.0) & (trace["time"] <= 52.0)]
    assert (spacing_window["mode"] == "spacing").mean() > 0.75

    emergency_window = trace[(trace["time"] >= 55.0) & (trace["time"] <= 61.0)]
    assert (emergency_window["mode"] == "emergency").any()

    recovery_window = trace[trace["time"] >= 61.5]
    assert (recovery_window["mode"] == "run").mean() > 0.8


def test_gap_and_summary_checks():
    trace = pd.read_csv(TRACE_PATH, dtype=str, keep_default_na=False)
    summary = yaml.safe_load(SUMMARY_PATH.read_text(encoding="utf-8"))

    no_lead = trace[trace["lead_present"] == "0"]
    assert (no_lead["segment"] == "").all()
    assert (no_lead["lead_speed"] == "").all()
    assert (no_lead["gap"] == "").all()

    with_lead = trace[trace["lead_present"] == "1"].copy()
    with_lead["gap_num"] = pd.to_numeric(with_lead["gap"])
    assert with_lead["gap_num"].min() >= 6.0

    assert summary["events"]["first_spacing_time"] == 18.0
    assert summary["events"]["first_emergency_time"] == 55.0
    assert summary["events"]["return_to_run_time"] == 61.5
    assert summary["checks"]["summary_ready"] is True


def main():
    tests = [
        ("required_files_exist", test_required_files_exist),
        ("input_config_integrity", test_input_config_integrity),
        ("trace_format", test_trace_format),
        ("trace_matches_oracle", test_trace_matches_oracle),
        ("summary_matches_oracle", test_summary_matches_oracle),
        ("modes_and_recovery", test_modes_and_recovery),
        ("gap_and_summary_checks", test_gap_and_summary_checks),
    ]

    for name, test in tests:
        test()
        print(f"{name}: ok")


if __name__ == "__main__":
    main()
