#!/bin/bash

set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
cd "$TASK_ROOT"

python3 <<'PY'
from pathlib import Path


dispatch_scheduler_code = '''"""Battery dispatch scheduler driven by nested YAML constraints."""


class BatteryPeakShavingScheduler:
    """Replay one day of facility load against a battery dispatch policy."""

    def __init__(self, config):
        self.config = config
        self.site = config["site"]
        self.schedule = config["schedule"]
        self.tariff = config["tariff"]
        self.battery = config["battery"]
        self.reserve = config["reserve"]
        self.preferences = config["dispatch_preferences"]
        self.dt_hours = float(self.schedule["dt_hours"])
        self.charge_windows = self.preferences["precharge_windows"]
        self.support_labels = {item["label"] for item in self.preferences["support_windows"]}
        self.export_allowed = bool(self.preferences["export_allowed"])
        self.reset()

    def reset(self):
        self.soc_mwh = float(self.battery["initial_soc_mwh"])

    def tariff_for_hour(self, hour):
        hour_int = int(hour)
        for window in self.tariff["windows"]:
            if int(window["start_hour"]) <= hour_int < int(window["end_hour"]):
                return window["label"]
        raise ValueError(f"No tariff window configured for hour {hour_int}")

    def reserve_floor_for_hour(self, hour):
        hour_int = int(hour)
        floor = float(self.reserve["terminal_min_soc_mwh"])
        for window in self.reserve.get("critical_windows", []):
            if hour_int < int(window["end_hour"]):
                floor = max(floor, float(window["min_soc_mwh"]))
        return floor

    def _precharge_target_for_hour(self, hour):
        hour_int = int(hour)
        target = None
        for window in self.charge_windows:
            if int(window["start_hour"]) <= hour_int < int(window["end_hour"]):
                target = float(window["target_soc_mwh"])
                break
        return target

    def dispatch_hour(self, hour, facility_load_kw):
        hour_int = int(hour)
        facility_load_kw = float(facility_load_kw)
        tariff_label = self.tariff_for_hour(hour_int)
        reserve_floor_mwh = self.reserve_floor_for_hour(hour_int)
        demand_cap_kw = float(self.preferences["demand_cap_kw"])

        battery_power_kw = 0.0
        action = "idle"

        precharge_target = self._precharge_target_for_hour(hour_int)
        if precharge_target is not None and self.soc_mwh < precharge_target - 1e-9:
            max_charge_kw = min(
                float(self.battery["max_charge_power_kw"]),
                (precharge_target - self.soc_mwh) * 1000.0 / float(self.battery["charge_efficiency"]) / self.dt_hours,
            )
            if not self.export_allowed:
                max_charge_kw = min(max_charge_kw, max(0.0, demand_cap_kw - facility_load_kw))
            if max_charge_kw > 1e-9:
                battery_power_kw = -max_charge_kw
                self.soc_mwh += (
                    max_charge_kw * float(self.battery["charge_efficiency"]) * self.dt_hours / 1000.0
                )
                action = "charge"
        elif tariff_label in self.support_labels and facility_load_kw > demand_cap_kw and self.soc_mwh > reserve_floor_mwh + 1e-9:
            available_discharge_kw = (
                (self.soc_mwh - reserve_floor_mwh)
                * 1000.0
                * float(self.battery["discharge_efficiency"])
                / self.dt_hours
            )
            discharge_kw = min(
                float(self.battery["max_discharge_power_kw"]),
                facility_load_kw - demand_cap_kw,
                available_discharge_kw,
            )
            if discharge_kw > 1e-9:
                battery_power_kw = discharge_kw
                self.soc_mwh -= (
                    discharge_kw * self.dt_hours / float(self.battery["discharge_efficiency"]) / 1000.0
                )
                action = "discharge"

        self.soc_mwh = min(float(self.battery["max_soc_mwh"]), max(float(self.battery["min_soc_mwh"]), self.soc_mwh))
        grid_power_kw = facility_load_kw - battery_power_kw
        if not self.export_allowed:
            grid_power_kw = max(0.0, grid_power_kw)

        return {
            "tariff_label": tariff_label,
            "battery_power_kw": round(battery_power_kw, 4),
            "grid_power_kw": round(grid_power_kw, 4),
            "soc_mwh": round(self.soc_mwh, 4),
            "reserve_floor_mwh": round(reserve_floor_mwh, 4),
            "action": action,
        }
'''


battery_peak_shaving_code = '''"""Run a battery peak-shaving replay from YAML constraints and CSV load data."""

import csv
from pathlib import Path

import yaml

from dispatch_scheduler import BatteryPeakShavingScheduler


BASE_DIR = Path(__file__).resolve().parent


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    config = load_yaml(BASE_DIR / "battery_constraints.yaml")["battery_peak_shaving"]
    load_rows_input = load_rows(BASE_DIR / "facility_load.csv")
    scheduler = BatteryPeakShavingScheduler(config)

    dt_hours = float(config["schedule"]["dt_hours"])
    energy_prices = config["tariff"]["energy_prices_usd_per_mwh"]
    demand_charge = float(config["tariff"]["demand_charge_usd_per_kw"])

    dispatch_rows = []
    baseline_energy_cost = 0.0
    optimized_energy_cost = 0.0
    baseline_peak_kw = 0.0
    optimized_peak_kw = 0.0
    total_charge_mwh = 0.0
    total_discharge_mwh = 0.0
    reserve_respected = True
    export_respected = True

    for row in load_rows_input:
        hour = int(row["hour"])
        facility_load_kw = float(row["facility_load_kw"])
        decision = scheduler.dispatch_hour(hour, facility_load_kw)
        tariff_label = decision["tariff_label"]
        grid_power_kw = float(decision["grid_power_kw"])
        battery_power_kw = float(decision["battery_power_kw"])

        baseline_energy_cost += facility_load_kw * dt_hours / 1000.0 * float(energy_prices[tariff_label])
        optimized_energy_cost += grid_power_kw * dt_hours / 1000.0 * float(energy_prices[tariff_label])
        baseline_peak_kw = max(baseline_peak_kw, facility_load_kw)
        optimized_peak_kw = max(optimized_peak_kw, grid_power_kw)

        if battery_power_kw < 0:
            total_charge_mwh += (-battery_power_kw) * dt_hours / 1000.0
        elif battery_power_kw > 0:
            total_discharge_mwh += battery_power_kw * dt_hours / 1000.0

        reserve_respected = reserve_respected and float(decision["soc_mwh"]) + 1e-9 >= float(decision["reserve_floor_mwh"])
        export_respected = export_respected and grid_power_kw >= -1e-9

        dispatch_rows.append(
            {
                "hour": hour,
                "tariff_label": tariff_label,
                "facility_load_kw": round(facility_load_kw, 4),
                "battery_power_kw": round(battery_power_kw, 4),
                "grid_power_kw": round(grid_power_kw, 4),
                "soc_mwh": round(float(decision["soc_mwh"]), 4),
                "reserve_floor_mwh": round(float(decision["reserve_floor_mwh"]), 4),
                "action": decision["action"],
            }
        )

    baseline_demand_charge = baseline_peak_kw * demand_charge
    optimized_demand_charge = optimized_peak_kw * demand_charge
    baseline_total_cost = baseline_energy_cost + baseline_demand_charge
    optimized_total_cost = optimized_energy_cost + optimized_demand_charge

    artifact = {
        "simulation": {
            "site_name": config["site"]["name"],
            "rows_processed": len(dispatch_rows),
            "dt_hours": dt_hours,
        },
        "summary": {
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
            "final_soc_mwh": round(float(dispatch_rows[-1]["soc_mwh"]), 4),
            "reserve_respected": bool(reserve_respected),
            "export_respected": bool(export_respected),
        },
        "dispatch_plan": dispatch_rows,
    }

    with open(BASE_DIR / "battery_dispatch_plan.yaml", "w", encoding="utf-8") as handle:
        yaml.dump(artifact, handle, default_flow_style=False, sort_keys=False)

    with open(BASE_DIR / "battery_dispatch_results.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "hour",
                "tariff_label",
                "facility_load_kw",
                "battery_power_kw",
                "grid_power_kw",
                "soc_mwh",
                "reserve_floor_mwh",
                "action",
            ],
        )
        writer.writeheader()
        writer.writerows(dispatch_rows)

    report = """# Battery Peak-Shaving Summary

## System Design
The simulator loads tariff windows, battery limits, reserve floors, and dispatch preferences from the YAML configuration and replays the 24-hour facility trace one hour at a time.

## Dispatch Strategy
The controller charges only during the configured precharge window and discharges during allowed support windows when facility demand exceeds the configured demand cap while keeping state of charge above the active reserve floor.

## Results Summary
Baseline peak demand was reduced from {baseline_peak:.1f} kW to {optimized_peak:.1f} kW and total operating cost dropped from ${baseline_total:.4f} to ${optimized_total:.4f}.
""".format(
        baseline_peak=baseline_peak_kw,
        optimized_peak=optimized_peak_kw,
        baseline_total=baseline_total_cost,
        optimized_total=optimized_total_cost,
    )
    (BASE_DIR / "battery_summary.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
'''


task_root = Path.cwd()
(task_root / "dispatch_scheduler.py").write_text(dispatch_scheduler_code, encoding="utf-8")
(task_root / "battery_peak_shaving.py").write_text(battery_peak_shaving_code, encoding="utf-8")
PY

python3 "$TASK_ROOT/battery_peak_shaving.py"
