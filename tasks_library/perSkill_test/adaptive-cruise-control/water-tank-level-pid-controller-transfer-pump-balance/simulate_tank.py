"""Run the liquid level closed-loop simulation."""

import math
from pathlib import Path

import pandas as pd
import yaml

from tank_controller import TankLevelController


def clip(value, low, high):
    return max(low, min(high, value))


def resolve_input(task_root, filename):
    direct = task_root / filename
    if direct.exists():
        return direct
    fallback = task_root / "environment" / filename
    return fallback


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


def run_simulation(task_root):
    task_root = Path(task_root)
    with open(resolve_input(task_root, "tank_config.yaml"), "r", encoding="utf-8") as f:
        base_config = yaml.safe_load(f)
    with open(task_root / "tank_tuning.yaml", "r", encoding="utf-8") as f:
        tuning = yaml.safe_load(f)

    config = {
        "tank": base_config["tank"],
        "pump": base_config["pump"],
        "simulation": base_config["simulation"],
        "pid": tuning["pid"],
    }

    tank = config["tank"]
    pump = config["pump"]
    simulation = config["simulation"]

    controller = TankLevelController(config)
    inflow_profile = pd.read_csv(resolve_input(task_root, "inflow_profile.csv"))

    dt = float(simulation["dt"])
    level_m = float(tank["initial_level_m"])
    actual_pump_lps = float(pump["initial_pump_lps"])
    rows = []

    for record in inflow_profile.itertuples(index=False):
        time_s = float(record.time_s)
        inflow_lps = float(record.inflow_lps)
        requested_pump_lps, level_error_m = controller.compute(
            target_level_m=tank["target_level_m"],
            actual_level_m=level_m,
            inflow_lps=inflow_lps,
            dt=dt,
        )

        max_step = float(pump["pump_ramp_limit_lps_per_s"]) * dt
        pump_delta = clip(requested_pump_lps - actual_pump_lps, -max_step, max_step)
        actual_pump_lps = clip(
            actual_pump_lps + pump_delta,
            float(pump["min_pump_lps"]),
            float(pump["max_pump_lps"]),
        )

        rows.append(
            {
                "time_s": time_s,
                "target_level_m": float(tank["target_level_m"]),
                "actual_level_m": level_m,
                "inflow_lps": inflow_lps,
                "requested_pump_lps": requested_pump_lps,
                "actual_pump_lps": actual_pump_lps,
                "level_error_m": level_error_m,
            }
        )

        gravity_outflow_lps = float(tank["outlet_coeff_lps_per_sqrt_m"]) * math.sqrt(
            max(level_m, 0.0)
        )
        total_outflow_lps = actual_pump_lps + gravity_outflow_lps
        level_m = clip(
            level_m + ((inflow_lps - total_outflow_lps) / float(tank["tank_area_m2"])) * dt,
            float(tank["min_level_m"]),
            float(tank["max_level_m"]),
        )

    trace = pd.DataFrame(rows)
    trace.to_csv(task_root / "tank_level_response.csv", index=False)
    return trace


def main():
    task_root = Path(__file__).resolve().parent
    run_simulation(task_root)


if __name__ == "__main__":
    main()
