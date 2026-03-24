"""Tests for the greenhouse climate transfer task."""

import importlib.util
import os
from pathlib import Path

import pandas as pd
import yaml


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestInputs:
    def test_input_files(self):
        with open(TASK_ROOT / "greenhouse_policies.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["greenhouse"]

        assert config["replay"]["dt_minutes"] == 10
        assert config["replay"]["duration_minutes"] == 120
        assert set(config["zones"].keys()) == {"propagation", "production"}
        assert config["fallback"]["max_missing_steps"] == 2

        trace = pd.read_csv(TASK_ROOT / "sensor_trace.csv")
        assert len(trace) == 26
        assert list(trace.columns) == [
            "time_min",
            "zone",
            "outside_temp_c",
            "outside_humidity_pct",
            "solar_wm2",
            "temp_sensor_c",
            "humidity_sensor_pct",
        ]
        assert trace["temp_sensor_c"].isna().sum() >= 2
        assert trace["humidity_sensor_pct"].isna().sum() >= 2


class TestZoneController:
    def test_controller_interface(self):
        module = load_module("zone_controller", TASK_ROOT / "zone_controller.py")
        with open(TASK_ROOT / "greenhouse_policies.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["greenhouse"]

        assert hasattr(module, "ZoneClimateController")
        controller = module.ZoneClimateController(
            "propagation",
            config["zones"]["propagation"],
            config,
        )
        controller.reset()
        result = controller.compute_controls(
            estimated_temp_c=22.0,
            estimated_humidity_pct=74.0,
            outside_temp_c=18.0,
            outside_humidity_pct=80.0,
            solar_wm2=300.0,
            fallback_active=False,
        )
        assert set(result.keys()) == {"heater_kw", "vent_pct", "mister_lpm"}
        assert 0.0 <= result["heater_kw"] <= config["zones"]["propagation"]["limits"]["heater_kw_max"]
        assert 0.0 <= result["vent_pct"] <= config["zones"]["propagation"]["limits"]["vent_pct_max"]
        assert 0.0 <= result["mister_lpm"] <= config["zones"]["propagation"]["limits"]["mister_lpm_max"]


class TestSimulationOutputs:
    def test_climate_simulation_csv(self):
        trace = pd.read_csv(TASK_ROOT / "sensor_trace.csv")
        simulation = pd.read_csv(TASK_ROOT / "climate_simulation.csv")

        assert list(simulation.columns) == [
            "time_min",
            "zone",
            "estimated_temp_c",
            "estimated_humidity_pct",
            "heater_kw",
            "vent_pct",
            "mister_lpm",
            "temp_in_band",
            "humidity_in_band",
            "fallback_applied",
        ]
        assert len(simulation) == len(trace)
        assert simulation["zone"].nunique() == 2
        assert set(simulation["fallback_applied"].astype(str).str.lower().unique()).issubset({"true", "false"})

    def test_strategy_yaml(self):
        with open(TASK_ROOT / "greenhouse_strategy.yaml", "r", encoding="utf-8") as handle:
            strategy = yaml.safe_load(handle)
        with open(TASK_ROOT / "greenhouse_policies.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)["greenhouse"]

        assert strategy["replay"]["rows_processed"] == 26
        assert strategy["replay"]["time_step_minutes"] == 10
        assert strategy["overall"]["zones_simulated"] == 2
        assert strategy["overall"]["all_temperature_ratios_ok"] is True
        assert strategy["overall"]["all_humidity_ratios_ok"] is True
        assert strategy["overall"]["all_constraints_ok"] is True

        for zone_name, zone_policy in config["zones"].items():
            zone_strategy = strategy["zones"][zone_name]
            assert zone_strategy["crop"] == zone_policy["crop"]
            assert zone_strategy["fallback_mode"]["missing_sensor_policy"] == "hold-last-then-estimate"
            assert zone_strategy["fallback_mode"]["max_missing_steps"] == 2
            assert zone_strategy["metrics"]["temperature_in_band_ratio"] >= 0.75
            assert zone_strategy["metrics"]["humidity_in_band_ratio"] >= 0.9
            assert zone_strategy["metrics"]["fallback_events"] >= 1
            assert zone_strategy["metrics"]["max_temperature_deviation_c"] < 1.0
            assert zone_strategy["metrics"]["max_humidity_deviation_pct"] < 1.0
            assert zone_strategy["derived_strategy"]["temperature_gain_kw_per_c"] > 0.0
            assert zone_strategy["derived_strategy"]["vent_gain_pct_per_c"] > 0.0
            assert zone_strategy["derived_strategy"]["mister_gain_lpm_per_pct"] > 0.0

    def test_report_sections(self):
        content = (TASK_ROOT / "greenhouse_report.md").read_text(encoding="utf-8").lower()
        assert "system design" in content
        assert "fallback handling" in content
        assert "replay results" in content
