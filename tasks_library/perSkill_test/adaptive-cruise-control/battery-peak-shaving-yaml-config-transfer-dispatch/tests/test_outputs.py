"""Tests for the battery peak-shaving transfer task."""

import importlib.util
import math
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


def load_config():
    with open(TASK_ROOT / "battery_constraints.yaml", "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)["battery_peak_shaving"]


def expected_tariff_for_hour(config, hour):
    hour = int(hour)
    for window in config["tariff"]["windows"]:
        if int(window["start_hour"]) <= hour < int(window["end_hour"]):
            return window["label"]
    raise AssertionError(f"no tariff window for hour {hour}")


def expected_reserve_floor(config, hour):
    hour = int(hour)
    floor = float(config["reserve"]["terminal_min_soc_mwh"])
    for window in config["reserve"].get("critical_windows", []):
        if hour < int(window["end_hour"]):
            floor = max(floor, float(window["min_soc_mwh"]))
    return round(floor, 4)


def expected_precharge_target(config, hour):
    hour = int(hour)
    for window in config["dispatch_preferences"]["precharge_windows"]:
        if int(window["start_hour"]) <= hour < int(window["end_hour"]):
            return float(window["target_soc_mwh"])
    return None


def simulate_expected_rows(config, trace):
    dt_hours = float(config["schedule"]["dt_hours"])
    charge_eff = float(config["battery"]["charge_efficiency"])
    discharge_eff = float(config["battery"]["discharge_efficiency"])
    max_charge = float(config["battery"]["max_charge_power_kw"])
    max_discharge = float(config["battery"]["max_discharge_power_kw"])
    min_soc = float(config["battery"]["min_soc_mwh"])
    max_soc = float(config["battery"]["max_soc_mwh"])
    demand_cap = float(config["dispatch_preferences"]["demand_cap_kw"])
    support_labels = {item["label"] for item in config["dispatch_preferences"]["support_windows"]}
    export_allowed = bool(config["dispatch_preferences"]["export_allowed"])

    soc_mwh = float(config["battery"]["initial_soc_mwh"])
    rows = []
    for row in trace.to_dict("records"):
        hour = int(row["hour"])
        facility_load_kw = float(row["facility_load_kw"])
        tariff_label = expected_tariff_for_hour(config, hour)
        reserve_floor_mwh = expected_reserve_floor(config, hour)

        battery_power_kw = 0.0
        action = "idle"

        precharge_target = expected_precharge_target(config, hour)
        if precharge_target is not None and soc_mwh < precharge_target - 1e-9:
            max_charge_kw = min(
                max_charge,
                (precharge_target - soc_mwh) * 1000.0 / charge_eff / dt_hours,
            )
            if not export_allowed:
                max_charge_kw = min(max_charge_kw, max(0.0, demand_cap - facility_load_kw))
            if max_charge_kw > 1e-9:
                battery_power_kw = -max_charge_kw
                soc_mwh += max_charge_kw * charge_eff * dt_hours / 1000.0
                action = "charge"
        elif (
            tariff_label in support_labels
            and facility_load_kw > demand_cap
            and soc_mwh > reserve_floor_mwh + 1e-9
        ):
            available_discharge_kw = (soc_mwh - reserve_floor_mwh) * 1000.0 * discharge_eff / dt_hours
            discharge_kw = min(
                max_discharge,
                facility_load_kw - demand_cap,
                available_discharge_kw,
            )
            if discharge_kw > 1e-9:
                battery_power_kw = discharge_kw
                soc_mwh -= discharge_kw * dt_hours / discharge_eff / 1000.0
                action = "discharge"

        soc_mwh = min(max_soc, max(min_soc, soc_mwh))
        grid_power_kw = facility_load_kw - battery_power_kw
        if not export_allowed:
            grid_power_kw = max(0.0, grid_power_kw)

        rows.append(
            {
                "hour": hour,
                "tariff_label": tariff_label,
                "facility_load_kw": round(facility_load_kw, 4),
                "battery_power_kw": round(battery_power_kw, 4),
                "grid_power_kw": round(grid_power_kw, 4),
                "soc_mwh": round(soc_mwh, 4),
                "reserve_floor_mwh": round(reserve_floor_mwh, 4),
                "action": action,
            }
        )
    return rows


def expected_summary(config, rows):
    dt_hours = float(config["schedule"]["dt_hours"])
    energy_prices = config["tariff"]["energy_prices_usd_per_mwh"]
    demand_charge = float(config["tariff"]["demand_charge_usd_per_kw"])

    baseline_energy_cost = 0.0
    optimized_energy_cost = 0.0
    baseline_peak_kw = 0.0
    optimized_peak_kw = 0.0
    total_charge_mwh = 0.0
    total_discharge_mwh = 0.0
    reserve_respected = True
    export_respected = True

    for row in rows:
        tariff_label = row["tariff_label"]
        facility_load_kw = float(row["facility_load_kw"])
        grid_power_kw = float(row["grid_power_kw"])
        battery_power_kw = float(row["battery_power_kw"])

        baseline_energy_cost += facility_load_kw * dt_hours / 1000.0 * float(energy_prices[tariff_label])
        optimized_energy_cost += grid_power_kw * dt_hours / 1000.0 * float(energy_prices[tariff_label])
        baseline_peak_kw = max(baseline_peak_kw, facility_load_kw)
        optimized_peak_kw = max(optimized_peak_kw, grid_power_kw)

        if battery_power_kw < 0:
            total_charge_mwh += (-battery_power_kw) * dt_hours / 1000.0
        elif battery_power_kw > 0:
            total_discharge_mwh += battery_power_kw * dt_hours / 1000.0

        reserve_respected = reserve_respected and float(row["soc_mwh"]) + 1e-9 >= float(row["reserve_floor_mwh"])
        export_respected = export_respected and float(row["grid_power_kw"]) >= -1e-9

    baseline_demand_charge = baseline_peak_kw * demand_charge
    optimized_demand_charge = optimized_peak_kw * demand_charge
    baseline_total_cost = baseline_energy_cost + baseline_demand_charge
    optimized_total_cost = optimized_energy_cost + optimized_demand_charge

    return {
        "baseline_energy_cost_usd": round(baseline_energy_cost, 4),
        "optimized_energy_cost_usd": round(optimized_energy_cost, 4),
        "baseline_demand_charge_usd": round(baseline_demand_charge, 4),
        "optimized_demand_charge_usd": round(optimized_demand_charge, 4),
        "baseline_total_cost_usd": round(baseline_total_cost, 4),
        "optimized_total_cost_usd": round(optimized_total_cost, 4),
        "cost_savings_usd": round(baseline_total_cost - optimized_total_cost, 4),
        "baseline_peak_kw": round(baseline_peak_kw, 4),
        "optimized_peak_kw": round(optimized_peak_kw, 4),
        "peak_reduction_kw": round(baseline_peak_kw - optimized_peak_kw, 4),
        "total_charge_mwh": round(total_charge_mwh, 4),
        "total_discharge_mwh": round(total_discharge_mwh, 4),
        "final_soc_mwh": round(float(rows[-1]["soc_mwh"]), 4),
        "reserve_respected": bool(reserve_respected),
        "export_respected": bool(export_respected),
    }


def assert_close(actual, expected, tol=1e-4):
    assert math.isclose(float(actual), float(expected), abs_tol=tol), (actual, expected)


class TestInputs:
    def test_input_files(self):
        config = load_config()

        assert config["schedule"]["dt_hours"] == 1.0
        assert config["schedule"]["horizon_hours"] == 24
        assert config["tariff"]["energy_prices_usd_per_mwh"]["off_peak"] == 70.0
        assert config["tariff"]["energy_prices_usd_per_mwh"]["mid_peak"] == 120.0
        assert config["tariff"]["energy_prices_usd_per_mwh"]["on_peak"] == 260.0
        assert config["tariff"]["demand_charge_usd_per_kw"] == 8.0
        assert config["battery"]["capacity_mwh"] == 4.0
        assert config["battery"]["initial_soc_mwh"] == 1.4
        assert config["battery"]["max_charge_power_kw"] == 600.0
        assert config["battery"]["max_discharge_power_kw"] == 700.0
        assert config["reserve"]["terminal_min_soc_mwh"] == 1.0
        assert config["reserve"]["critical_windows"][0]["min_soc_mwh"] == 1.4
        assert config["dispatch_preferences"]["demand_cap_kw"] == 2200.0
        assert config["dispatch_preferences"]["export_allowed"] is False

        trace = pd.read_csv(TASK_ROOT / "facility_load.csv")
        assert len(trace) == 24
        assert list(trace.columns) == ["hour", "facility_load_kw"]
        assert trace["hour"].iloc[0] == 0
        assert trace["hour"].iloc[-1] == 23
        assert trace["facility_load_kw"].max() == 2550


class TestSchedulerInterface:
    def test_scheduler_interface(self):
        module = load_module("dispatch_scheduler", TASK_ROOT / "dispatch_scheduler.py")
        config = load_config()

        assert hasattr(module, "BatteryPeakShavingScheduler")
        scheduler = module.BatteryPeakShavingScheduler(config)
        scheduler.reset()

        assert scheduler.tariff_for_hour(0) == expected_tariff_for_hour(config, 0)
        assert scheduler.tariff_for_hour(10) == expected_tariff_for_hour(config, 10)
        assert scheduler.tariff_for_hour(18) == expected_tariff_for_hour(config, 18)
        assert scheduler.reserve_floor_for_hour(5) == expected_reserve_floor(config, 5)
        assert scheduler.reserve_floor_for_hour(20) == expected_reserve_floor(config, 20)
        assert scheduler.reserve_floor_for_hour(22) == expected_reserve_floor(config, 22)

        first = scheduler.dispatch_hour(hour=0, facility_load_kw=1500)
        assert set(first.keys()) == {
            "tariff_label",
            "battery_power_kw",
            "grid_power_kw",
            "soc_mwh",
            "reserve_floor_mwh",
            "action",
        }
        assert first["tariff_label"] == expected_tariff_for_hour(config, 0)
        assert first["action"] == "charge"
        assert first["battery_power_kw"] < 0
        assert first["grid_power_kw"] > 1500
        assert first["reserve_floor_mwh"] == expected_reserve_floor(config, 0)


class TestReplayOutputs:
    def test_results_csv_matches_rule_replay(self):
        config = load_config()
        trace = pd.read_csv(TASK_ROOT / "facility_load.csv")
        results = pd.read_csv(TASK_ROOT / "battery_dispatch_results.csv")
        expected_rows = simulate_expected_rows(config, trace)
        expected = pd.DataFrame(expected_rows)

        assert list(results.columns) == [
            "hour",
            "tariff_label",
            "facility_load_kw",
            "battery_power_kw",
            "grid_power_kw",
            "soc_mwh",
            "reserve_floor_mwh",
            "action",
        ]
        assert len(results) == len(trace)

        pd.testing.assert_series_equal(results["hour"], expected["hour"], check_names=False)
        pd.testing.assert_series_equal(results["tariff_label"], expected["tariff_label"], check_names=False)
        pd.testing.assert_series_equal(results["action"], expected["action"], check_names=False)
        for column in [
            "facility_load_kw",
            "battery_power_kw",
            "grid_power_kw",
            "soc_mwh",
            "reserve_floor_mwh",
        ]:
            for actual, expected_value in zip(results[column], expected[column]):
                assert_close(actual, expected_value)

        assert results["grid_power_kw"].ge(0.0).all()
        assert results["soc_mwh"].between(
            float(config["battery"]["min_soc_mwh"]),
            float(config["battery"]["max_soc_mwh"]),
        ).all()
        assert results["grid_power_kw"].max() <= float(config["dispatch_preferences"]["demand_cap_kw"]) + 1e-4
        assert results.loc[results["hour"] == 23, "soc_mwh"].iloc[0] >= float(config["reserve"]["terminal_min_soc_mwh"])

    def test_dispatch_yaml_matches_results_and_summary_formulas(self):
        config = load_config()
        trace = pd.read_csv(TASK_ROOT / "facility_load.csv")
        expected_rows = simulate_expected_rows(config, trace)
        expected_summary_data = expected_summary(config, expected_rows)

        with open(TASK_ROOT / "battery_dispatch_plan.yaml", "r", encoding="utf-8") as handle:
            artifact = yaml.safe_load(handle)

        assert artifact["simulation"]["site_name"] == config["site"]["name"]
        assert artifact["simulation"]["rows_processed"] == len(expected_rows)
        assert artifact["simulation"]["dt_hours"] == float(config["schedule"]["dt_hours"])

        summary = artifact["summary"]
        for key, expected_value in expected_summary_data.items():
            if isinstance(expected_value, bool):
                assert summary[key] is expected_value
            else:
                assert_close(summary[key], expected_value)

        assert summary["optimized_total_cost_usd"] < summary["baseline_total_cost_usd"]
        assert summary["optimized_peak_kw"] <= float(config["dispatch_preferences"]["demand_cap_kw"]) + 1e-4

        plan = artifact["dispatch_plan"]
        assert len(plan) == len(expected_rows)
        for actual_row, expected_row in zip(plan, expected_rows):
            assert actual_row["hour"] == expected_row["hour"]
            assert actual_row["tariff_label"] == expected_row["tariff_label"]
            assert actual_row["action"] == expected_row["action"]
            for key in [
                "facility_load_kw",
                "battery_power_kw",
                "grid_power_kw",
                "soc_mwh",
                "reserve_floor_mwh",
            ]:
                assert_close(actual_row[key], expected_row[key])

    def test_report_sections(self):
        content = (TASK_ROOT / "battery_summary.md").read_text(encoding="utf-8").lower()
        assert "system design" in content
        assert "dispatch strategy" in content
        assert "results summary" in content
