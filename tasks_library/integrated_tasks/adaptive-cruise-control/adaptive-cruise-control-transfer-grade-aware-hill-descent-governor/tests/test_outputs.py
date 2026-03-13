"""Tests for the Transfer grade-aware hill descent governor task."""

from __future__ import annotations

import csv
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, "/root")

ROOT = Path("/root")
STEADY_WINDOWS = [(0.0, 37.0), (53.0, 67.0), (83.0, 92.0), (108.0, 142.0), (158.0, 180.0)]
SETTLING_KEYS = {
    "after_target_drop_45s": 45.0,
    "after_grade_step_75s": 75.0,
    "after_target_drop_100s": 100.0,
    "after_target_change_150s": 150.0,
}


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def in_windows(time_value: float, windows):
    return any(start <= time_value <= end for start, end in windows)


def settling_time(df: pd.DataFrame, change_time: float, band: float = 0.35, samples: int = 6):
    start_indices = df.index[df["time"] == change_time].tolist()
    assert start_indices, f"Missing change time {change_time}"
    start_index = start_indices[0]
    for index in range(start_index, len(df) - samples + 1):
        window = df.iloc[index:index + samples]
        if (window["speed_error"].abs() <= band).all():
            return float(window.iloc[0]["time"] - change_time)
    return None


class TestInputFiles:
    def test_profiles_and_yaml_are_intact(self):
        grade = pd.read_csv(ROOT / "grade_profile.csv")
        target = pd.read_csv(ROOT / "target_speed_profile.csv")

        assert list(grade.columns) == ["time", "grade_percent"]
        assert list(target.columns) == ["time", "target_speed"]
        assert len(grade) == 361
        assert len(target) == 361
        assert grade["time"].iloc[0] == 0.0
        assert grade["time"].iloc[-1] == 180.0
        assert target["time"].equals(grade["time"])
        assert grade.loc[grade["time"] == 0.0, "grade_percent"].iloc[0] == 4.0
        assert grade.loc[grade["time"] == 75.0, "grade_percent"].iloc[0] == 8.0
        assert grade.loc[grade["time"] == 150.0, "grade_percent"].iloc[0] == 5.0
        assert target.loc[target["time"] == 0.0, "target_speed"].iloc[0] == 24.0
        assert target.loc[target["time"] == 45.0, "target_speed"].iloc[0] == 22.0
        assert target.loc[target["time"] == 100.0, "target_speed"].iloc[0] == 20.0
        assert target.loc[target["time"] == 150.0, "target_speed"].iloc[0] == 19.0

        with open(ROOT / "descent_vehicle.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        assert config["vehicle"]["mass_kg"] == 2800.0
        assert config["vehicle"]["max_service_brake_decel_mps2"] == 5.5
        assert config["controller"]["initial_speed_mps"] == 24.0
        assert config["controller"]["settling_error_band_mps"] == 0.35
        assert config["controller"]["settling_samples"] == 6
        assert config["pid_brake"] == {"kp": 0.28, "ki": 0.015, "kd": 0.0}
        assert config["simulation"]["dt"] == 0.5
        assert config["simulation"]["duration_s"] == 180.0


class TestPIDController:
    def test_pid_controller_basics(self):
        module = load_module("/root/pid_controller.py", "pid_controller")
        ctrl = module.PIDController(1.0, 0.2, 0.0, output_limits=(0.0, 5.0), integral_limit=10.0)
        ctrl.reset()
        first = ctrl.compute(1.0, 0.5)
        second = ctrl.compute(1.0, 0.5)
        assert isinstance(first, float)
        assert second > first

        ctrl = module.PIDController(2.0, 0.0, 0.0)
        ctrl.reset()
        small = ctrl.compute(1.0, 0.5)
        ctrl.reset()
        large = ctrl.compute(2.0, 0.5)
        assert large > small


class TestGovernor:
    def test_return_shape_and_grade_awareness(self):
        module = load_module("/root/hill_descent_governor.py", "hill_descent_governor")
        with open(ROOT / "descent_vehicle.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        with open(ROOT / "descent_tuning.yaml", "r", encoding="utf-8") as handle:
            config["pid_brake_tuned"] = yaml.safe_load(handle)["pid_brake"]

        governor = module.HillDescentGovernor(config)
        output = governor.compute(vehicle_speed=22.0, target_speed=21.5, grade_percent=5.0, dt=0.5)
        assert isinstance(output, tuple)
        assert len(output) == 3

        mild = governor.compute(vehicle_speed=22.0, target_speed=21.5, grade_percent=4.0, dt=0.5)
        steep = governor.compute(vehicle_speed=22.0, target_speed=21.5, grade_percent=9.0, dt=0.5)
        assert steep[1] > mild[1]
        assert 0.0 <= mild[0] <= 1.0
        assert 0.0 <= steep[0] <= 1.0


class TestTuningFile:
    def test_tuning_structure_and_ranges(self):
        with open(ROOT / "descent_tuning.yaml", "r", encoding="utf-8") as handle:
            tuning = yaml.safe_load(handle)

        assert set(tuning.keys()) == {"pid_brake"}
        assert set(tuning["pid_brake"].keys()) == {"kp", "ki", "kd"}
        assert 0 < tuning["pid_brake"]["kp"] < 10
        assert 0 <= tuning["pid_brake"]["ki"] < 5
        assert 0 <= tuning["pid_brake"]["kd"] < 5
        assert tuning["pid_brake"] != {"kp": 0.28, "ki": 0.015, "kd": 0.0}


class TestSimulationOutput:
    def test_csv_shape_columns_and_physics(self):
        grade = pd.read_csv(ROOT / "grade_profile.csv")
        target = pd.read_csv(ROOT / "target_speed_profile.csv")
        results = pd.read_csv(ROOT / "descent_simulation_results.csv")

        assert list(results.columns) == [
            "time",
            "grade_percent",
            "target_speed",
            "vehicle_speed",
            "speed_error",
            "brake_command",
            "brake_decel",
            "gravity_accel",
            "drag_accel",
            "rolling_accel",
            "net_accel",
        ]
        assert len(results) == 361
        assert results["time"].equals(grade["time"])
        assert results["grade_percent"].equals(grade["grade_percent"])
        assert results["target_speed"].equals(target["target_speed"])
        assert (results["brake_command"] >= -1e-9).all()
        assert (results["brake_command"] <= 1.0 + 1e-9).all()
        assert (results["brake_decel"] >= -1e-9).all()
        assert (results["brake_decel"] <= 5.5 + 1e-9).all()

        reconstructed = (
            results["gravity_accel"]
            - results["drag_accel"]
            - results["rolling_accel"]
            - results["brake_decel"]
        )
        assert (reconstructed.sub(results["net_accel"]).abs() < 1e-9).all()

        next_speed = results["vehicle_speed"] + results["net_accel"] * 0.5
        speed_error = next_speed.iloc[:-1].reset_index(drop=True) - results["vehicle_speed"].iloc[1:].reset_index(drop=True)
        assert speed_error.abs().max() < 1e-9


class TestPerformanceTargets:
    def test_tracking_settling_and_brake_blending(self):
        results = pd.read_csv(ROOT / "descent_simulation_results.csv")
        steady = results[results["time"].apply(lambda value: in_windows(value, STEADY_WINDOWS))]

        assert results["speed_error"].max() < 2.2
        assert steady["speed_error"].max() < 0.5
        assert steady["speed_error"].abs().mean() < 0.15

        expected_limits = {
            "after_target_drop_45s": 4.0,
            "after_grade_step_75s": 2.0,
            "after_target_drop_100s": 4.0,
            "after_target_change_150s": 4.0,
        }
        for key, change_time in SETTLING_KEYS.items():
            value = settling_time(results, change_time)
            assert value is not None
            assert value < expected_limits[key]

        long_segment = results[(results["time"] >= 110.0) & (results["time"] <= 145.0)]
        assert long_segment["brake_command"].mean() > 0.08
        assert long_segment["brake_command"].max() > 0.1

        assert results["vehicle_speed"].max() <= 24.5


class TestMetricsFile:
    def test_metrics_yaml_matches_outputs(self):
        results = pd.read_csv(ROOT / "descent_simulation_results.csv")
        steady = results[results["time"].apply(lambda value: in_windows(value, STEADY_WINDOWS))]

        with open(ROOT / "descent_metrics.yaml", "r", encoding="utf-8") as handle:
            metrics = yaml.safe_load(handle)

        assert set(metrics.keys()) == {
            "max_transient_overspeed_mps",
            "steady_max_overspeed_mps",
            "steady_mean_abs_error_mps",
            "settling_times_s",
            "safety",
        }
        assert abs(metrics["max_transient_overspeed_mps"] - results["speed_error"].max()) < 1e-9
        assert abs(metrics["steady_max_overspeed_mps"] - steady["speed_error"].max()) < 1e-9
        assert abs(metrics["steady_mean_abs_error_mps"] - steady["speed_error"].abs().mean()) < 1e-9

        for key, change_time in SETTLING_KEYS.items():
            recomputed = settling_time(results, change_time)
            assert abs(metrics["settling_times_s"][key] - recomputed) < 1e-9

        assert abs(metrics["safety"]["max_vehicle_speed_mps"] - results["vehicle_speed"].max()) < 1e-9
        assert abs(metrics["safety"]["max_brake_decel_mps2"] - results["brake_decel"].max()) < 1e-9
        assert metrics["safety"]["within_service_brake_limit"] is True


class TestSimulationExecution:
    def test_simulation_uses_both_csv_profiles(self):
        base_results = pd.read_csv(ROOT / "descent_simulation_results.csv")
        base_final_mean = base_results[base_results["time"] >= 165.0]["vehicle_speed"].mean()
        base_long_brake = base_results[(base_results["time"] >= 120.0) & (base_results["time"] <= 180.0)]["brake_command"].mean()

        target_backup = ROOT / "target_speed_profile.original.csv"
        grade_backup = ROOT / "grade_profile.original.csv"
        shutil.copy(ROOT / "target_speed_profile.csv", target_backup)
        shutil.copy(ROOT / "grade_profile.csv", grade_backup)

        try:
            target_rows = []
            with open(ROOT / "target_speed_profile.csv", "r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    time_value = float(row["time"])
                    target_speed = float(row["target_speed"])
                    if time_value >= 150.0:
                        target_speed -= 1.5
                    target_rows.append({"time": time_value, "target_speed": target_speed})
            with open(ROOT / "target_speed_profile.csv", "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "target_speed"])
                writer.writeheader()
                writer.writerows(target_rows)

            subprocess.run(["python3", "descent_simulation.py"], cwd=ROOT, check=True, timeout=60)
            changed_target = pd.read_csv(ROOT / "descent_simulation_results.csv")
            changed_final_mean = changed_target[changed_target["time"] >= 165.0]["vehicle_speed"].mean()
            assert changed_final_mean < base_final_mean - 0.6

            shutil.copy(grade_backup, ROOT / "grade_profile.csv")
            shutil.copy(target_backup, ROOT / "target_speed_profile.csv")

            grade_rows = []
            with open(ROOT / "grade_profile.csv", "r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    time_value = float(row["time"])
                    grade_percent = float(row["grade_percent"])
                    if time_value >= 120.0:
                        grade_percent = max(0.0, grade_percent - 3.0)
                    grade_rows.append({"time": time_value, "grade_percent": grade_percent})
            with open(ROOT / "grade_profile.csv", "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["time", "grade_percent"])
                writer.writeheader()
                writer.writerows(grade_rows)

            subprocess.run(["python3", "descent_simulation.py"], cwd=ROOT, check=True, timeout=60)
            changed_grade = pd.read_csv(ROOT / "descent_simulation_results.csv")
            changed_long_brake = changed_grade[(changed_grade["time"] >= 120.0) & (changed_grade["time"] <= 180.0)]["brake_command"].mean()
            assert changed_long_brake < base_long_brake - 0.02
        finally:
            shutil.copy(target_backup, ROOT / "target_speed_profile.csv")
            shutil.copy(grade_backup, ROOT / "grade_profile.csv")
            subprocess.run(["python3", "descent_simulation.py"], cwd=ROOT, check=True, timeout=60)
