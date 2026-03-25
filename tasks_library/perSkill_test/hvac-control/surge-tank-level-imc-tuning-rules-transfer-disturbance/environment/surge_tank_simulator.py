#!/usr/bin/env python3

import csv
import json
from pathlib import Path


def _round(value):
    return round(float(value), 6)


def load_case(case_path):
    with open(case_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_schedule(schedule_path):
    intervals = []
    with open(schedule_path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            intervals.append(
                {
                    "segment_id": row["segment_id"],
                    "start_min": float(row["start_min"]),
                    "end_min": float(row["end_min"]),
                    "disturbance_percent": float(row["disturbance_percent"]),
                }
            )
    return intervals


def controller_from_lambda(case_data, lambda_min):
    K = case_data["process_model"]["K"]
    tau = case_data["process_model"]["tau_min"]
    return {
        "Kp": _round(tau / (K * lambda_min)),
        "Ki": _round(1.0 / (K * lambda_min)),
        "Kd": 0.0,
    }


def disturbance_at_time(schedule, time_min):
    for interval in schedule:
        if interval["start_min"] <= time_min < interval["end_min"]:
            return interval["disturbance_percent"]
    if schedule:
        return schedule[-1]["disturbance_percent"]
    return 0.0


def disturbance_clear_time(schedule):
    nonzero = [interval["end_min"] for interval in schedule if abs(interval["disturbance_percent"]) > 1e-12]
    if not nonzero:
        return 0.0
    return max(nonzero)


def run_closed_loop(case_data, schedule, lambda_min):
    controller = controller_from_lambda(case_data, lambda_min)
    operating = case_data["operating_point"]
    limits = case_data["valve_limits_percent"]
    duration = case_data["simulation"]["duration_min"]
    dt = case_data["simulation"]["dt_min"]

    setpoint = operating["setpoint_level_percent"]
    level = operating["initial_level_percent"]
    bias = operating["nominal_valve_percent"]
    integral = 0.0
    time_min = 0.0

    trajectory = [
        {
            "time_min": _round(time_min),
            "level_percent": _round(level),
            "setpoint_percent": _round(setpoint),
            "valve_percent": _round(bias),
            "disturbance_percent": _round(disturbance_at_time(schedule, time_min)),
            "error_percent": _round(setpoint - level),
        }
    ]

    K = case_data["process_model"]["K"]
    tau = case_data["process_model"]["tau_min"]
    steps = int(round(duration / dt))

    for step in range(steps):
        disturbance = disturbance_at_time(schedule, time_min)
        error = setpoint - level
        integral += error * dt

        raw_valve = bias + controller["Kp"] * error + controller["Ki"] * integral
        valve = max(limits["min"], min(limits["max"], raw_valve))

        dlevel_dt = (-(level - setpoint) + K * (valve - bias) + disturbance) / tau
        level += dlevel_dt * dt
        time_min = (step + 1) * dt

        trajectory.append(
            {
                "time_min": _round(time_min),
                "level_percent": _round(level),
                "setpoint_percent": _round(setpoint),
                "valve_percent": _round(valve),
                "disturbance_percent": _round(disturbance_at_time(schedule, time_min)),
                "error_percent": _round(setpoint - level),
            }
        )

    return trajectory


def summarize_trajectory(case_data, schedule, trajectory):
    acceptance = case_data["acceptance"]
    setpoint = case_data["operating_point"]["setpoint_level_percent"]
    clear_time = disturbance_clear_time(schedule)
    band = acceptance["stability_band_percent"]

    level_values = [point["level_percent"] for point in trajectory]
    valve_values = [point["valve_percent"] for point in trajectory]
    after_clear = [point for point in trajectory if point["time_min"] >= clear_time]

    recovery_time = None
    for idx, point in enumerate(trajectory):
        if point["time_min"] < clear_time:
            continue
        if abs(point["level_percent"] - setpoint) <= band:
            tail = trajectory[idx:]
            if all(abs(item["level_percent"] - setpoint) <= band for item in tail):
                recovery_time = point["time_min"] - clear_time
                break

    peak_rebound = 0.0
    if after_clear:
        peak_rebound = max(0.0, max(point["level_percent"] for point in after_clear) - setpoint)

    final_level = trajectory[-1]["level_percent"]
    final_error = setpoint - final_level

    return {
        "recovery_time_min": None if recovery_time is None else _round(recovery_time),
        "peak_rebound_above_setpoint_percent": _round(peak_rebound),
        "lowest_level_percent": _round(min(level_values)),
        "max_valve_percent": _round(max(valve_values)),
        "min_valve_percent": _round(min(valve_values)),
        "final_level_percent": _round(final_level),
        "final_error_percent": _round(final_error),
    }


def candidate_result(case_data, schedule, lambda_min):
    metrics = summarize_trajectory(case_data, schedule, run_closed_loop(case_data, schedule, lambda_min))
    acceptance = case_data["acceptance"]
    meets_constraints = (
        metrics["recovery_time_min"] is not None
        and metrics["recovery_time_min"] <= acceptance["max_recovery_time_after_disturbance_min"]
        and metrics["peak_rebound_above_setpoint_percent"] <= acceptance["max_rebound_above_setpoint_percent"]
    )
    return {
        "lambda_min": _round(lambda_min),
        "controller": controller_from_lambda(case_data, lambda_min),
        "metrics": metrics,
        "meets_constraints": meets_constraints,
    }


def evaluate_candidates(case_data, schedule):
    return [candidate_result(case_data, schedule, value) for value in case_data["candidate_lambda_min"]]
