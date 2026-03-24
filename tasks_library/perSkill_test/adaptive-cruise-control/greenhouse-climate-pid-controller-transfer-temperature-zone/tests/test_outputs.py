import importlib.util
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


def compute_metrics(trace):
    settling_minute = None
    for start in range(0, len(trace) - 19):
        window = trace.iloc[start:start + 20]
        if (window["temp_error"].abs() <= 0.4).all():
            settling_minute = int(window["time_min"].iloc[0])
            break

    cold_snap = trace[(trace["time_min"] >= 120.0) & (trace["time_min"] <= 180.0)]
    solar_window = trace[(trace["time_min"] >= 240.0) & (trace["time_min"] <= 300.0)]
    final_window = trace[(trace["time_min"] >= 330.0) & (trace["time_min"] <= 360.0)]

    return {
        "settling_minute": settling_minute,
        "cold_snap_max_error": float(cold_snap["temp_error"].abs().max()),
        "solar_overshoot": float((solar_window["zone_temp"] - solar_window["setpoint_temp"]).max()),
        "final_window_mae": float(final_window["temp_error"].abs().mean()),
    }


class TestInputAssets:
    def test_input_assets_unchanged(self):
        config = yaml.safe_load((ROOT / "greenhouse_config.yaml").read_text())
        assert config["greenhouse"]["initial_zone_temp_c"] == 20.5
        assert config["greenhouse"]["setpoint_temp_c"] == 22.0
        assert config["greenhouse"]["min_heater_power_kw"] == 0.0
        assert config["greenhouse"]["max_heater_power_kw"] == 7.0
        assert config["greenhouse"]["heat_loss_coeff_kw_per_c"] == 0.2
        assert config["greenhouse"]["thermal_capacity_kwh_per_c"] == 3.0
        assert config["simulation"]["dt_minutes"] == 1.0
        assert config["simulation"]["duration_minutes"] == 360
        assert config["simulation"]["integral_limit"] == 40.0

        weather = pd.read_csv(ROOT / "weather_profile.csv")
        assert list(weather.columns) == ["time_min", "outside_temp_c", "solar_gain_kw"]
        assert len(weather) == 361
        assert weather["time_min"].iloc[0] == 0.0
        assert weather["time_min"].iloc[-1] == 360.0
        assert weather["outside_temp_c"].between(5.0, 13.0).all()
        assert weather["solar_gain_kw"].between(0.0, 3.2).all()


class TestPIDController:
    def test_pid_controller_class(self):
        module = load_module("pid_controller", ROOT / "pid_controller.py")
        ctrl = module.PIDController(
            kp=1.0,
            ki=0.5,
            kd=0.2,
            output_min=-2.0,
            output_max=2.0,
            integral_limit=4.0,
        )
        assert hasattr(ctrl, "reset")
        assert hasattr(ctrl, "compute")

        ctrl.reset()
        out1 = ctrl.compute(error=1.0, dt=0.1)
        out2 = ctrl.compute(error=1.0, dt=0.1)
        assert isinstance(out1, float)
        assert out2 > out1

        ctrl.reset()
        bounded = ctrl.compute(error=-20.0, dt=0.1)
        assert bounded >= -2.0


class TestGreenhouseController:
    def test_greenhouse_controller(self):
        module = load_module("greenhouse_controller", ROOT / "greenhouse_controller.py")
        base_config = yaml.safe_load((ROOT / "greenhouse_config.yaml").read_text())
        tuning = yaml.safe_load((ROOT / "greenhouse_tuning.yaml").read_text())
        config = {
            "greenhouse": base_config["greenhouse"],
            "pid_initial": base_config["pid_initial"],
            "simulation": base_config["simulation"],
            "pid": tuning["pid"],
        }

        controller = module.GreenhouseTemperatureController(config)
        heater_power_kw, temp_error = controller.compute(
            setpoint_temp=22.0,
            zone_temp=21.2,
            outside_temp=8.0,
            solar_gain_kw=0.4,
            dt_minutes=1.0,
        )
        assert isinstance(heater_power_kw, float)
        assert isinstance(temp_error, float)
        assert abs(temp_error - 0.8) < 1e-9
        assert 0.0 <= heater_power_kw <= 7.0


class TestTuningFile:
    def test_tuning_values_and_metrics(self):
        tuning = yaml.safe_load((ROOT / "greenhouse_tuning.yaml").read_text())
        config = yaml.safe_load((ROOT / "greenhouse_config.yaml").read_text())
        trace = pd.read_csv(ROOT / "greenhouse_temperature_log.csv")
        computed = compute_metrics(trace)

        assert set(tuning.keys()) == {"pid", "metrics"}
        assert set(tuning["pid"].keys()) == {"kp", "ki", "kd"}
        assert set(tuning["metrics"].keys()) == {
            "settling_minute",
            "cold_snap_max_error",
            "solar_overshoot",
            "final_window_mae",
        }

        assert 0 < tuning["pid"]["kp"] < 10
        assert 0 <= tuning["pid"]["ki"] < 5
        assert 0 <= tuning["pid"]["kd"] < 5
        assert (
            tuning["pid"]["kp"] != config["pid_initial"]["kp"]
            or tuning["pid"]["ki"] != config["pid_initial"]["ki"]
            or tuning["pid"]["kd"] != config["pid_initial"]["kd"]
        )

        assert abs(tuning["metrics"]["settling_minute"] - computed["settling_minute"]) <= 1
        assert abs(tuning["metrics"]["cold_snap_max_error"] - computed["cold_snap_max_error"]) <= 0.02
        assert abs(tuning["metrics"]["solar_overshoot"] - computed["solar_overshoot"]) <= 0.02
        assert abs(tuning["metrics"]["final_window_mae"] - computed["final_window_mae"]) <= 0.02


class TestSimulationOutputs:
    def test_log_shape_and_weather_alignment(self):
        trace = pd.read_csv(ROOT / "greenhouse_temperature_log.csv")
        weather = pd.read_csv(ROOT / "weather_profile.csv")

        assert list(trace.columns) == [
            "time_min",
            "setpoint_temp",
            "zone_temp",
            "outside_temp",
            "solar_gain_kw",
            "heater_power_kw",
            "net_heat_kw",
            "temp_error",
        ]
        assert len(trace) == 361
        assert np.allclose(trace["time_min"].values, weather["time_min"].values)
        assert np.allclose(trace["outside_temp"].values, weather["outside_temp_c"].values)
        assert np.allclose(trace["solar_gain_kw"].values, weather["solar_gain_kw"].values)

    def test_heat_balance_recurrence_and_limits(self):
        trace = pd.read_csv(ROOT / "greenhouse_temperature_log.csv")
        config = yaml.safe_load((ROOT / "greenhouse_config.yaml").read_text())
        greenhouse = config["greenhouse"]
        dt_hours = config["simulation"]["dt_minutes"] / 60.0

        assert (trace["heater_power_kw"] >= greenhouse["min_heater_power_kw"] - 1e-9).all()
        assert (trace["heater_power_kw"] <= greenhouse["max_heater_power_kw"] + 1e-9).all()
        assert trace["heater_power_kw"].std() > 0.05

        exchange = greenhouse["heat_loss_coeff_kw_per_c"] * (trace["zone_temp"] - trace["outside_temp"])
        expected_net = trace["heater_power_kw"] + trace["solar_gain_kw"] - exchange
        assert np.allclose(trace["net_heat_kw"].values, expected_net.values, atol=5e-4)

        next_expected = trace["zone_temp"].iloc[:-1] + (
            trace["net_heat_kw"].iloc[:-1] / greenhouse["thermal_capacity_kwh_per_c"]
        ) * dt_hours
        assert np.allclose(trace["zone_temp"].iloc[1:].values, next_expected.values, atol=5e-4)


class TestPerformanceTargets:
    def test_temperature_performance(self):
        trace = pd.read_csv(ROOT / "greenhouse_temperature_log.csv")
        metrics = compute_metrics(trace)

        assert metrics["settling_minute"] is not None
        assert metrics["settling_minute"] < 80
        assert metrics["cold_snap_max_error"] < 0.20
        assert metrics["solar_overshoot"] < 0.35
        assert metrics["final_window_mae"] < 0.18


class TestNotes:
    def test_notes_keywords(self):
        content = (ROOT / "climate_notes.md").read_text()
        assert "热模型" in content
        assert "调节" in content or "调参" in content
        assert "冷空气" in content
        assert "日照" in content
