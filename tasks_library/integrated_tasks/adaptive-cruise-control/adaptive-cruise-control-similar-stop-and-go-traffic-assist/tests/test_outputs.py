"""Tests for the Similar stop-and-go traffic jam assist task."""

from __future__ import annotations

import importlib.util
import sys

import pandas as pd
import yaml

sys.path.insert(0, "/root")


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stop_segments(df: pd.DataFrame):
    segments = []
    in_stop = False
    start = None
    for row in df.itertuples():
        is_stop = pd.notna(row.lead_speed) and row.ego_speed <= 0.3
        if is_stop and not in_stop:
            start = row.time
            in_stop = True
        elif in_stop and not is_stop:
            segments.append((start, round(row.time - 0.1, 1)))
            in_stop = False
    if in_stop:
        segments.append((start, float(df.iloc[-1]["time"])))
    return segments


class TestInputFiles:
    def test_radar_trace_and_yaml_are_intact(self):
        radar = pd.read_csv("/root/jam_radar_trace.csv")
        assert list(radar.columns) == ["time", "lead_speed", "distance_hint"]
        assert len(radar) == 1801
        assert radar["time"].iloc[0] == 0.0
        assert radar["time"].iloc[-1] == 180.0
        assert radar["distance_hint"].notna().sum() == 1
        first_hint = radar[radar["distance_hint"].notna()].iloc[0]
        assert first_hint["time"] == 15.0
        assert first_hint["distance_hint"] == 55.0

        with open("/root/jam_vehicle.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        assert config["vehicle"]["max_acceleration"] == 2.8
        assert config["vehicle"]["max_deceleration"] == -5.5
        assert config["jam_assist"]["set_speed"] == 22.0
        assert config["jam_assist"]["time_headway"] == 1.8
        assert config["jam_assist"]["min_gap"] == 8.0
        assert config["jam_assist"]["emergency_ttc_threshold"] == 2.2
        assert config["comfort"]["jerk_limit"] == 2.4
        assert config["simulation"]["dt"] == 0.1
        assert config["simulation"]["duration"] == 180.0


class TestPIDController:
    def test_pid_controller_basics(self):
        module = load_module("/root/pid_controller.py", "pid_controller")
        ctrl = module.PIDController(1.0, 0.1, 0.0, output_limits=(-2.0, 2.0), integral_limit=5.0)
        ctrl.reset()
        first = ctrl.compute(1.0, 0.1)
        second = ctrl.compute(1.0, 0.1)
        assert isinstance(first, float)
        assert second > first

        ctrl = module.PIDController(2.0, 0.0, 0.0)
        ctrl.reset()
        out_small = ctrl.compute(1.0, 0.1)
        ctrl.reset()
        out_large = ctrl.compute(2.0, 0.1)
        assert out_large > out_small


class TestJamAssistSystem:
    def test_modes_and_return_shape(self):
        module = load_module("/root/jam_assist_system.py", "jam_assist_system")
        with open("/root/jam_vehicle.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        assist = module.TrafficJamAssist(config)

        cruise = assist.compute(ego_speed=18.0, lead_speed=None, gap_to_lead=None, dt=0.1)
        assert isinstance(cruise, tuple)
        assert len(cruise) == 4
        assert cruise[1] == "cruise"

        follow = assist.compute(ego_speed=18.0, lead_speed=16.0, gap_to_lead=45.0, dt=0.1)
        assert follow[1] == "follow"
        assert isinstance(follow[2], float)
        assert isinstance(follow[3], float)

        hold = assist.compute(ego_speed=0.2, lead_speed=0.0, gap_to_lead=9.0, dt=0.1)
        assert hold[1] == "stop_hold"
        assert hold[0] <= 0.0

        emergency = assist.compute(ego_speed=18.0, lead_speed=0.0, gap_to_lead=10.0, dt=0.1)
        assert emergency[1] == "emergency"
        assert emergency[0] < 0.0


class TestTuningFile:
    def test_tuning_structure_and_ranges(self):
        with open("/root/jam_tuning.yaml", "r", encoding="utf-8") as handle:
            tuning = yaml.safe_load(handle)
        assert set(tuning.keys()) == {"pid_speed", "pid_gap"}
        for key in ["pid_speed", "pid_gap"]:
            assert set(tuning[key].keys()) == {"kp", "ki", "kd"}
            assert 0 < tuning[key]["kp"] < 10
            assert 0 <= tuning[key]["ki"] < 5
            assert 0 <= tuning[key]["kd"] < 5

        assert tuning["pid_speed"] != {"kp": 0.18, "ki": 0.02, "kd": 0.0}
        assert tuning["pid_gap"] != {"kp": 0.16, "ki": 0.02, "kd": 0.0}


class TestSimulationOutput:
    def test_csv_shape_limits_and_simulated_gap(self):
        radar = pd.read_csv("/root/jam_radar_trace.csv")
        results = pd.read_csv("/root/jam_results.csv")

        assert list(results.columns) == [
            "time",
            "ego_speed",
            "lead_speed",
            "gap_to_lead",
            "acceleration_cmd",
            "jerk",
            "mode",
            "gap_error",
            "target_gap",
        ]
        assert len(results) == 1801
        assert results["time"].equals(radar["time"])
        assert results["lead_speed"].fillna(-1.0).equals(radar["lead_speed"].fillna(-1.0))
        assert results["gap_to_lead"].notna().sum() >= 1300
        assert results.loc[results["time"] == 15.0, "gap_to_lead"].iloc[0] == 55.0
        assert (results["acceleration_cmd"] <= 2.8 + 1e-9).all()
        assert (results["acceleration_cmd"] >= -5.5 - 1e-9).all()
        assert results["jerk"].abs().quantile(0.95) < 2.5

        gap_series = results["gap_to_lead"].fillna(-1.0)
        hint_series = radar["distance_hint"].fillna(-1.0)
        assert not gap_series.equals(hint_series)


class TestPerformanceTargets:
    def test_cruise_speed_gap_restart_and_settling(self):
        results = pd.read_csv("/root/jam_results.csv")

        first_clear = results[(results["time"] >= 12.0) & (results["time"] <= 15.0)]
        second_clear = results[(results["time"] >= 160.0) & (results["time"] <= 170.0)]
        assert abs(first_clear["ego_speed"].mean() - 22.0) < 0.6
        assert abs(second_clear["ego_speed"].mean() - 22.0) < 0.6
        assert results["ego_speed"].max() < 23.0

        lead_rows = results[results["gap_to_lead"].notna()]
        assert lead_rows["gap_to_lead"].min() > 6.0

        segments = stop_segments(results)
        assert len(segments) >= 2
        for start, end in segments[:2]:
            window = results[(results["time"] >= start) & (results["time"] <= end)]
            assert len(window) >= 8
            restart_row = results[results["time"] == round(end + 5.0, 1)]
            assert not restart_row.empty
            assert restart_row.iloc[0]["ego_speed"] > 5.0

        for start, end in [(56.0, 64.0), (98.0, 106.0), (136.0, 146.0)]:
            window = results[(results["time"] >= start) & (results["time"] <= end) & (results["mode"] == "follow")]
            assert window["gap_error"].abs().mean() < 1.5


class TestReport:
    def test_primary_report_mentions_required_topics(self):
        with open("/root/jam_assist_report.md", "r", encoding="utf-8") as handle:
            content = handle.read().lower()
        for keyword in ["design", "tuning", "comfort", "settling", "stop-and-go"]:
            assert keyword in content
