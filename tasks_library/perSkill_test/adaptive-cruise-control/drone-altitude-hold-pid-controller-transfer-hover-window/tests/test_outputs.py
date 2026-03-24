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


def expand_mission(mission_df, dt, duration):
    rows = []
    for idx in range(int(round(duration / dt)) + 1):
        t = round(idx * dt, 1)
        row = mission_df[
            (mission_df["start_time"] <= t + 1e-9)
            & ((mission_df["end_time"] > t + 1e-9) | (abs(mission_df["end_time"] - duration) < 1e-9))
        ].iloc[0]
        rows.append({"time": t, "target_altitude": float(row["target_altitude_m"])})
    return pd.DataFrame(rows)


def expand_gusts(gust_df, dt, duration):
    rows = []
    for idx in range(int(round(duration / dt)) + 1):
        t = round(idx * dt, 1)
        active = gust_df[
            (gust_df["start_time"] <= t + 1e-9)
            & ((gust_df["end_time"] > t + 1e-9) | (abs(gust_df["end_time"] - duration) < 1e-9))
        ]
        gust_accel = float(active["gust_accel_mps2"].sum()) if len(active) else 0.0
        rows.append({"time": t, "gust_accel": gust_accel})
    return pd.DataFrame(rows)


class TestInputAssets:
    def test_input_assets_unchanged(self):
        config = yaml.safe_load((ROOT / "drone_config.yaml").read_text())
        assert config["drone"]["initial_altitude_m"] == 12.0
        assert config["drone"]["max_climb_rate_mps"] == 3.0
        assert config["drone"]["max_sink_rate_mps"] == -3.0
        assert config["drone"]["max_collective_accel_mps2"] == 2.8
        assert config["drone"]["min_collective_accel_mps2"] == -3.5
        assert config["drone"]["vertical_damping"] == 0.55
        assert config["simulation"]["dt"] == 0.2
        assert config["simulation"]["duration"] == 90.0
        assert config["simulation"]["integral_limit"] == 12.0

        mission = pd.read_csv(ROOT / "mission_profile.csv")
        assert list(mission.columns) == [
            "segment_id",
            "start_time",
            "end_time",
            "target_altitude_m",
        ]
        assert len(mission) == 6
        assert mission["target_altitude_m"].tolist() == [12.0, 17.0, 17.0, 13.0, 19.0, 16.0]

        gusts = pd.read_csv(ROOT / "gust_windows.csv")
        assert list(gusts.columns) == ["start_time", "end_time", "gust_accel_mps2"]
        assert len(gusts) == 4
        assert gusts["gust_accel_mps2"].tolist() == [-0.8, -1.0, 0.75, -0.65]


class TestPIDController:
    def test_pid_controller_class(self):
        module = load_module("pid_controller", ROOT / "pid_controller.py")
        ctrl = module.PIDController(
            kp=1.0, ki=0.5, kd=0.2, output_min=-2.0, output_max=2.0, integral_limit=4.0
        )
        assert hasattr(ctrl, "reset")
        assert hasattr(ctrl, "compute")

        ctrl.reset()
        out1 = ctrl.compute(error=1.0, dt=0.2)
        out2 = ctrl.compute(error=1.0, dt=0.2)
        assert isinstance(out1, float)
        assert out2 > out1

        ctrl.reset()
        bounded = ctrl.compute(error=-10.0, dt=0.2)
        assert bounded >= -2.0


class TestAltitudeController:
    def test_altitude_hold_controller(self):
        module = load_module("altitude_controller", ROOT / "altitude_controller.py")
        tuning = yaml.safe_load((ROOT / "altitude_tuning.yaml").read_text())
        config = yaml.safe_load((ROOT / "drone_config.yaml").read_text())
        runtime_config = {
            "drone": config["drone"],
            "simulation": config["simulation"],
            "pid": tuning["pid"],
        }

        controller = module.AltitudeHoldController(runtime_config)
        command, altitude_error = controller.compute(
            target_altitude=17.0,
            actual_altitude=15.5,
            vertical_speed=0.2,
            dt=0.2,
        )
        assert isinstance(command, float)
        assert isinstance(altitude_error, float)
        assert abs(altitude_error - 1.5) < 1e-9
        assert config["drone"]["min_collective_accel_mps2"] <= command <= config["drone"]["max_collective_accel_mps2"]


class TestTuningFile:
    def test_tuning_values(self):
        tuning = yaml.safe_load((ROOT / "altitude_tuning.yaml").read_text())
        config = yaml.safe_load((ROOT / "drone_config.yaml").read_text())

        assert set(tuning.keys()) == {"pid", "metrics"}
        assert set(tuning["pid"].keys()) == {"kp", "ki", "kd"}
        assert 0 < tuning["pid"]["kp"] < 10
        assert 0 <= tuning["pid"]["ki"] < 5
        assert 0 <= tuning["pid"]["kd"] < 5

        assert (
            tuning["pid"]["kp"] != config["pid_initial"]["kp"]
            or tuning["pid"]["ki"] != config["pid_initial"]["ki"]
            or tuning["pid"]["kd"] != config["pid_initial"]["kd"]
        )

        assert set(tuning["metrics"].keys()) == {
            "worst_post_gust_mae",
            "max_step_window_mae",
            "final_hover_mae",
        }


class TestTraceOutputs:
    def test_trace_shape_and_profile(self):
        trace = pd.read_csv(ROOT / "altitude_hold_trace.csv")
        config = yaml.safe_load((ROOT / "drone_config.yaml").read_text())
        mission = pd.read_csv(ROOT / "mission_profile.csv")
        gusts = pd.read_csv(ROOT / "gust_windows.csv")

        expected_target = expand_mission(mission, config["simulation"]["dt"], config["simulation"]["duration"])
        expected_gusts = expand_gusts(gusts, config["simulation"]["dt"], config["simulation"]["duration"])

        assert list(trace.columns) == [
            "time",
            "target_altitude",
            "actual_altitude",
            "vertical_speed",
            "collective_cmd",
            "gust_accel",
            "altitude_error",
        ]
        assert len(trace) == 451
        assert np.allclose(trace["time"].values, expected_target["time"].values)
        assert np.allclose(trace["target_altitude"].values, expected_target["target_altitude"].values)
        assert np.allclose(trace["gust_accel"].values, expected_gusts["gust_accel"].values)

    def test_limits_and_dynamics(self):
        trace = pd.read_csv(ROOT / "altitude_hold_trace.csv")
        config = yaml.safe_load((ROOT / "drone_config.yaml").read_text())

        assert (trace["collective_cmd"] <= config["drone"]["max_collective_accel_mps2"] + 1e-9).all()
        assert (trace["collective_cmd"] >= config["drone"]["min_collective_accel_mps2"] - 1e-9).all()
        assert (trace["actual_altitude"] >= 0.0).all()
        assert trace["collective_cmd"].std() > 0.05
        assert trace["actual_altitude"].max() > 18.0
        assert trace["actual_altitude"].min() >= 0.0


class TestPerformanceTargets:
    def test_hover_window_performance(self):
        trace = pd.read_csv(ROOT / "altitude_hold_trace.csv")

        gust_window_1 = trace[(trace["time"] >= 10.0) & (trace["time"] <= 15.0)]
        gust_window_2 = trace[(trace["time"] >= 37.0) & (trace["time"] <= 42.0)]
        rise_window_1 = trace[(trace["time"] >= 21.0) & (trace["time"] <= 30.0)]
        rise_window_2 = trace[(trace["time"] >= 66.0) & (trace["time"] <= 75.0)]
        descent_window = trace[(trace["time"] >= 55.0) & (trace["time"] <= 60.0)]
        final_window = trace[(trace["time"] >= 84.0) & (trace["time"] <= 90.0)]

        gust_mae_1 = gust_window_1["altitude_error"].abs().mean()
        gust_mae_2 = gust_window_2["altitude_error"].abs().mean()
        max_step_mae = max(
            rise_window_1["altitude_error"].abs().mean(),
            rise_window_2["altitude_error"].abs().mean(),
        )
        descent_mae = descent_window["altitude_error"].abs().mean()
        final_mae = final_window["altitude_error"].abs().mean()

        assert gust_mae_1 < 0.35
        assert gust_mae_2 < 0.35
        assert max_step_mae < 0.25
        assert descent_mae < 0.30
        assert final_mae < 0.10


class TestReport:
    def test_report_keywords(self):
        content = (ROOT / "hover_analysis.md").read_text().lower()
        assert "design" in content
        assert "tuning" in content
        assert "gust" in content
        assert "hover" in content
