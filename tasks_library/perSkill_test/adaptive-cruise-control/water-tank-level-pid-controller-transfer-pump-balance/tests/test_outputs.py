import importlib.util
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
sys.path.insert(0, str(ROOT))


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def asset_path(filename):
    direct = ROOT / filename
    if direct.exists():
        return direct
    return ROOT / "environment" / filename


def compute_metrics(trace):
    initial = trace[(trace["time_s"] >= 15.0) & (trace["time_s"] <= 25.0)]
    surge = trace[(trace["time_s"] >= 54.0) & (trace["time_s"] <= 66.0)]
    final = trace[(trace["time_s"] >= 100.0) & (trace["time_s"] <= 120.0)]
    return {
        "initial_recovery_mae": float(initial["level_error_m"].abs().mean()),
        "surge_recovery_mae": float(surge["level_error_m"].abs().mean()),
        "final_window_mae": float(final["level_error_m"].abs().mean()),
        "peak_level_m": float(trace["actual_level_m"].max()),
    }


class TestInputAssets:
    def test_input_assets_unchanged(self):
        config = yaml.safe_load(asset_path("tank_config.yaml").read_text())
        assert config["tank"]["tank_area_m2"] == 4.2
        assert config["tank"]["min_level_m"] == 0.5
        assert config["tank"]["max_level_m"] == 2.5
        assert config["tank"]["initial_level_m"] == 1.35
        assert config["tank"]["target_level_m"] == 1.7
        assert config["tank"]["outlet_coeff_lps_per_sqrt_m"] == 0.85
        assert config["pump"]["min_pump_lps"] == 0.0
        assert config["pump"]["max_pump_lps"] == 4.8
        assert config["pump"]["initial_pump_lps"] == 1.8
        assert config["pump"]["pump_ramp_limit_lps_per_s"] == 0.8
        assert config["simulation"]["dt"] == 0.5
        assert config["simulation"]["duration"] == 120.0
        assert config["simulation"]["nominal_inflow_lps"] == 3.1
        assert config["simulation"]["integral_limit"] == 10.0

        inflow = pd.read_csv(asset_path("inflow_profile.csv"))
        assert list(inflow.columns) == ["time_s", "inflow_lps"]
        assert len(inflow) == 241
        assert inflow["time_s"].iloc[0] == 0.0
        assert inflow["time_s"].iloc[-1] == 120.0
        assert np.allclose(np.diff(inflow["time_s"].values), 0.5)
        assert inflow["inflow_lps"].between(2.35, 4.40).all()


class TestPIDController:
    def test_pid_controller_class(self):
        module = load_module("pid_controller", ROOT / "pid_controller.py")
        ctrl = module.PIDController(
            kp=1.0, ki=0.6, kd=0.1, output_min=-2.0, output_max=2.0, integral_limit=3.0
        )
        assert hasattr(ctrl, "reset")
        assert hasattr(ctrl, "compute")

        ctrl.reset()
        out1 = ctrl.compute(error=1.0, dt=0.5)
        out2 = ctrl.compute(error=1.0, dt=0.5)
        assert isinstance(out1, float)
        assert out2 > out1

        ctrl.reset()
        bounded = ctrl.compute(error=20.0, dt=0.5)
        assert bounded <= 2.0


class TestTankController:
    def test_tank_level_controller(self):
        module = load_module("tank_controller", ROOT / "tank_controller.py")
        base_config = yaml.safe_load(asset_path("tank_config.yaml").read_text())
        tuning = yaml.safe_load((ROOT / "tank_tuning.yaml").read_text())
        config = {
            "tank": base_config["tank"],
            "pump": base_config["pump"],
            "simulation": base_config["simulation"],
            "pid": tuning["pid"],
        }

        controller = module.TankLevelController(config)
        requested_pump_lps, level_error_m = controller.compute(
            target_level_m=1.7,
            actual_level_m=1.55,
            inflow_lps=3.2,
            dt=0.5,
        )
        assert isinstance(requested_pump_lps, float)
        assert isinstance(level_error_m, float)
        assert abs(level_error_m - 0.15) < 1e-9
        assert 0.0 <= requested_pump_lps <= 4.8


class TestTuningFile:
    def test_tuning_values_and_metrics(self):
        tuning = yaml.safe_load((ROOT / "tank_tuning.yaml").read_text())
        config = yaml.safe_load(asset_path("tank_config.yaml").read_text())
        trace = pd.read_csv(ROOT / "tank_level_response.csv")
        metrics = compute_metrics(trace)

        assert set(tuning.keys()) == {"pid", "metrics"}
        assert set(tuning["pid"].keys()) == {"kp", "ki", "kd"}
        assert set(tuning["metrics"].keys()) == {
            "initial_recovery_mae",
            "surge_recovery_mae",
            "final_window_mae",
            "peak_level_m",
        }

        assert 0 < tuning["pid"]["kp"] < 10
        assert 0 <= tuning["pid"]["ki"] < 5
        assert 0 <= tuning["pid"]["kd"] < 5
        assert (
            tuning["pid"]["kp"] != config["pid_initial"]["kp"]
            or tuning["pid"]["ki"] != config["pid_initial"]["ki"]
            or tuning["pid"]["kd"] != config["pid_initial"]["kd"]
        )

        assert abs(tuning["metrics"]["initial_recovery_mae"] - metrics["initial_recovery_mae"]) <= 0.02
        assert abs(tuning["metrics"]["surge_recovery_mae"] - metrics["surge_recovery_mae"]) <= 0.02
        assert abs(tuning["metrics"]["final_window_mae"] - metrics["final_window_mae"]) <= 0.02
        assert abs(tuning["metrics"]["peak_level_m"] - metrics["peak_level_m"]) <= 0.02


class TestSimulationOutputs:
    def test_response_shape_and_profile_alignment(self):
        trace = pd.read_csv(ROOT / "tank_level_response.csv")
        inflow = pd.read_csv(asset_path("inflow_profile.csv"))
        target_level = yaml.safe_load(asset_path("tank_config.yaml").read_text())["tank"]["target_level_m"]

        assert list(trace.columns) == [
            "time_s",
            "target_level_m",
            "actual_level_m",
            "inflow_lps",
            "requested_pump_lps",
            "actual_pump_lps",
            "level_error_m",
        ]
        assert len(trace) == 241
        assert np.allclose(trace["time_s"].values, inflow["time_s"].values)
        assert np.allclose(trace["inflow_lps"].values, inflow["inflow_lps"].values)
        assert np.allclose(trace["target_level_m"].values, target_level)

    def test_level_recurrence_and_limits(self):
        trace = pd.read_csv(ROOT / "tank_level_response.csv")
        config = yaml.safe_load(asset_path("tank_config.yaml").read_text())
        tank = config["tank"]
        pump = config["pump"]
        dt = config["simulation"]["dt"]

        assert (trace["requested_pump_lps"] >= pump["min_pump_lps"] - 1e-9).all()
        assert (trace["requested_pump_lps"] <= pump["max_pump_lps"] + 1e-9).all()
        assert (trace["actual_pump_lps"] >= pump["min_pump_lps"] - 1e-9).all()
        assert (trace["actual_pump_lps"] <= pump["max_pump_lps"] + 1e-9).all()
        assert (trace["actual_level_m"] >= tank["min_level_m"] - 1e-9).all()
        assert (trace["actual_level_m"] <= tank["max_level_m"] + 1e-9).all()
        assert trace["actual_pump_lps"].std() > 0.05
        assert (trace["requested_pump_lps"] - trace["actual_pump_lps"]).abs().max() > 0.05

        pump_step = trace["actual_pump_lps"].diff().abs().dropna()
        assert (pump_step <= pump["pump_ramp_limit_lps_per_s"] * dt + 1e-9).all()

        gravity = tank["outlet_coeff_lps_per_sqrt_m"] * np.sqrt(np.clip(trace["actual_level_m"].values[:-1], 0.0, None))
        expected_next = trace["actual_level_m"].values[:-1] + (
            (trace["inflow_lps"].values[:-1] - (trace["actual_pump_lps"].values[:-1] + gravity))
            / tank["tank_area_m2"]
        ) * dt
        expected_next = np.clip(expected_next, tank["min_level_m"], tank["max_level_m"])
        assert np.allclose(trace["actual_level_m"].values[1:], expected_next, atol=5e-4)


class TestPerformanceTargets:
    def test_level_control_performance(self):
        trace = pd.read_csv(ROOT / "tank_level_response.csv")
        metrics = compute_metrics(trace)

        assert metrics["initial_recovery_mae"] < 0.08
        assert metrics["surge_recovery_mae"] < 0.10
        assert metrics["final_window_mae"] < 0.03
        assert metrics["peak_level_m"] < 1.95


class TestReport:
    def test_report_keywords(self):
        content = (ROOT / "level_control_report.md").read_text()
        assert "液位" in content
        assert "调节" in content or "调参" in content
        assert "扰动" in content
        assert "泵" in content
