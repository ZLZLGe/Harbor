import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path("/root")
OUTPUT_FILE = ROOT / "stop_go_gap_results.csv"
SCRIPT_FILE = ROOT / "gap_assist.py"


def load_yaml(path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def clamp(value, low, high):
    return max(low, min(high, value))


def segment_for_time(t, segments):
    for index, segment in enumerate(segments):
        is_last = index == len(segments) - 1
        if segment["start_s"] <= t and (t < segment["end_s"] or (is_last and t <= segment["end_s"])):
            return segment
    raise ValueError(f"No segment covers t={t}")


def lead_state(t, segments):
    segment = segment_for_time(t, segments)
    span = segment["end_s"] - segment["start_s"]
    ratio = 0.0 if span == 0 else (t - segment["start_s"]) / span
    ratio = clamp(ratio, 0.0, 1.0)
    speed = segment["start_speed_mps"] + (segment["end_speed_mps"] - segment["start_speed_mps"]) * ratio
    visible = 1 if segment["visible"] else 0
    return visible, speed


def build_reference_results():
    config = load_yaml(ROOT / "scenario_config.yaml")
    schedule = load_yaml(ROOT / "lead_schedule.yaml")
    segments = schedule["segments"]

    duration = config["simulation"]["duration_s"]
    dt = config["simulation"]["dt"]
    steps = int(round(duration / dt)) + 1

    ego_position = config["simulation"]["initial_ego_position_m"]
    ego_speed = config["simulation"]["initial_ego_speed_mps"]
    lead_position = config["lead_vehicle"]["initial_position_m"]

    rows = []
    for step in range(steps):
        t = round(step * dt, 10)
        lead_visible, lead_speed = lead_state(t, segments)
        gap = lead_position - ego_position
        safe_gap = config["gap_policy"]["min_gap_m"] + config["gap_policy"]["headway_s"] * ego_speed
        relative_speed = ego_speed - lead_speed
        ttc = math.inf if relative_speed <= 0 else gap / relative_speed

        if lead_visible == 0:
            mode = "cruise"
        elif gap <= config["mode_thresholds"]["emergency_factor"] * safe_gap or ttc < config["gap_policy"]["emergency_ttc_s"]:
            mode = "emergency"
        elif gap <= config["mode_thresholds"]["follow_factor"] * safe_gap:
            mode = "follow"
        else:
            mode = "cruise"

        if mode == "cruise":
            acceleration_cmd = config["controller"]["cruise_gain"] * (
                config["simulation"]["target_speed_mps"] - ego_speed
            )
        elif mode == "follow":
            acceleration_cmd = (
                config["controller"]["follow_gap_gain"] * (gap - safe_gap)
                + config["controller"]["follow_speed_gain"] * (lead_speed - ego_speed)
            )
        else:
            acceleration_cmd = config["vehicle"]["max_brake_mps2"]

        acceleration_cmd = clamp(
            acceleration_cmd,
            config["vehicle"]["max_brake_mps2"],
            config["vehicle"]["max_accel_mps2"],
        )

        rows.append(
            {
                "time": t,
                "lead_visible": lead_visible,
                "ego_position_m": ego_position,
                "ego_speed_mps": ego_speed,
                "lead_position_m": lead_position,
                "lead_speed_mps": lead_speed,
                "gap_m": gap,
                "safe_gap_m": safe_gap,
                "ttc_s": ttc,
                "mode": mode,
                "acceleration_cmd_mps2": acceleration_cmd,
            }
        )

        if step == steps - 1:
            continue

        next_time = round((step + 1) * dt, 10)
        _, next_lead_speed = lead_state(next_time, segments)

        ego_position = ego_position + ego_speed * dt + 0.5 * acceleration_cmd * dt * dt
        ego_speed = clamp(
            ego_speed + acceleration_cmd * dt,
            0.0,
            config["vehicle"]["max_speed_mps"],
        )
        lead_position = lead_position + 0.5 * (lead_speed + next_lead_speed) * dt

    return pd.DataFrame(rows)


class TestInputs:
    def test_config_assets_unchanged(self):
        config = load_yaml(ROOT / "scenario_config.yaml")
        schedule = load_yaml(ROOT / "lead_schedule.yaml")

        assert config["simulation"]["duration_s"] == 180.0
        assert config["simulation"]["dt"] == 0.2
        assert config["simulation"]["target_speed_mps"] == 30.0
        assert config["vehicle"]["max_accel_mps2"] == 2.8
        assert config["vehicle"]["max_brake_mps2"] == -7.5
        assert config["gap_policy"]["headway_s"] == 1.6
        assert config["gap_policy"]["emergency_ttc_s"] == 2.6
        assert config["mode_thresholds"]["follow_factor"] == 1.4
        assert config["mode_thresholds"]["emergency_factor"] == 0.9

        segments = schedule["segments"]
        assert len(segments) == 8
        assert segments[0]["start_s"] == 0.0
        assert segments[-1]["end_s"] == 180.0
        assert segments[0]["visible"] is False
        assert segments[4]["visible"] is False
        assert segments[5]["end_speed_mps"] == 7.0


class TestScript:
    def test_gap_assist_script_exists(self):
        assert SCRIPT_FILE.exists(), "gap_assist.py must exist"

        spec = importlib.util.spec_from_file_location("gap_assist", SCRIPT_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


class TestOutput:
    def test_output_exists_and_shape(self):
        assert OUTPUT_FILE.exists(), "stop_go_gap_results.csv must be generated"
        actual = pd.read_csv(OUTPUT_FILE)

        assert actual.columns.tolist() == [
            "time",
            "lead_visible",
            "ego_position_m",
            "ego_speed_mps",
            "lead_position_m",
            "lead_speed_mps",
            "gap_m",
            "safe_gap_m",
            "ttc_s",
            "mode",
            "acceleration_cmd_mps2",
        ]
        assert len(actual) == 901
        assert actual["time"].iloc[0] == 0.0
        assert actual["time"].iloc[-1] == 180.0

    def test_output_matches_reference_simulation(self):
        actual = pd.read_csv(OUTPUT_FILE)
        expected = build_reference_results()

        assert actual["mode"].tolist() == expected["mode"].tolist()
        assert actual["lead_visible"].astype(int).tolist() == expected["lead_visible"].astype(int).tolist()

        numeric_columns = [
            "time",
            "ego_position_m",
            "ego_speed_mps",
            "lead_position_m",
            "lead_speed_mps",
            "gap_m",
            "safe_gap_m",
            "ttc_s",
            "acceleration_cmd_mps2",
        ]
        for column in numeric_columns:
            actual_values = actual[column].to_numpy(dtype=float)
            expected_values = expected[column].to_numpy(dtype=float)
            assert np.allclose(actual_values, expected_values, rtol=1e-9, atol=1e-9, equal_nan=True), column

    def test_behavioral_landmarks(self):
        actual = pd.read_csv(OUTPUT_FILE)

        def row_at(time_value):
            match = actual[np.isclose(actual["time"], time_value)]
            assert len(match) == 1, time_value
            return match.iloc[0]

        assert row_at(0.0)["mode"] == "cruise"
        assert int(row_at(0.0)["lead_visible"]) == 0
        assert row_at(30.0)["mode"] == "follow"
        assert row_at(36.8)["mode"] == "emergency"
        assert row_at(72.0)["mode"] == "cruise"
        assert int(row_at(72.0)["lead_visible"]) == 0
        assert row_at(100.0)["mode"] == "follow"
        assert actual["gap_m"].min() > 10.0
        assert set(actual["mode"].unique()) == {"cruise", "follow", "emergency"}
