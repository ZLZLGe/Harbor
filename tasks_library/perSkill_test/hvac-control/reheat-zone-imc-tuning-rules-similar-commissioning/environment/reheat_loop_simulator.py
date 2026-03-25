#!/usr/bin/env python3

import json
from pathlib import Path


def load_case(path="/root/reheat_commissioning_case.json"):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def round_float(value, digits=6):
    return round(float(value), digits)


def calculate_pi_gains(K, tau_sec, lambda_sec):
    return {
        "Kp": round_float(tau_sec / (K * lambda_sec)),
        "Ki": round_float(1.0 / (K * lambda_sec)),
        "Kd": 0.0,
    }


def simulate_closed_loop(case_data, lambda_sec):
    process = case_data["process"]
    operating = case_data["operating_point"]
    simulation = case_data["simulation"]
    gains = calculate_pi_gains(process["K"], process["tau_sec"], lambda_sec)

    dt_sec = simulation["dt_sec"]
    total_steps = int(simulation["duration_sec"] / dt_sec)
    valve_min = operating["valve_min_percent"]
    valve_max = operating["valve_max_percent"]
    setpoint = operating["setpoint_c"]
    ambient = operating["ambient_temp_c"]
    zone_temp = operating["initial_zone_temp_c"]
    integral_state = 0.0
    integral_limit = simulation["integral_clamp_error_seconds"]
    trajectory = []

    for step_index in range(total_steps):
        error = setpoint - zone_temp
        proposed_integral = max(-integral_limit, min(integral_limit, integral_state + error * dt_sec))
        raw_valve = gains["Kp"] * error + gains["Ki"] * proposed_integral
        valve = max(valve_min, min(valve_max, raw_valve))
        if valve == raw_valve:
            integral_state = proposed_integral

        dtemp_dt = ((ambient + process["K"] * valve) - zone_temp) / process["tau_sec"]
        zone_temp += dtemp_dt * dt_sec

        trajectory.append(
            {
                "time_sec": round_float((step_index + 1) * dt_sec, 2),
                "zone_temp_c": round_float(zone_temp),
                "setpoint_c": round_float(setpoint),
                "valve_percent": round_float(valve),
                "error_c": round_float(setpoint - zone_temp),
            }
        )

    return trajectory


def compute_metrics(trajectory, case_data):
    operating = case_data["operating_point"]
    acceptance = case_data["acceptance"]

    initial_temp = operating["initial_zone_temp_c"]
    setpoint = operating["setpoint_c"]
    step_change = setpoint - initial_temp
    rise_threshold = initial_temp + 0.9 * step_change
    settling_band = acceptance["settling_band_c"]
    max_temp = max(point["zone_temp_c"] for point in trajectory)

    rise_time_sec = None
    for point in trajectory:
        if point["zone_temp_c"] >= rise_threshold:
            rise_time_sec = point["time_sec"]
            break

    settling_time_sec = None
    for index, point in enumerate(trajectory):
        if all(abs(item["zone_temp_c"] - setpoint) <= settling_band for item in trajectory[index:]):
            settling_time_sec = point["time_sec"]
            break

    saturated_samples = sum(1 for point in trajectory if point["valve_percent"] >= operating["valve_max_percent"])

    return {
        "rise_time_sec": rise_time_sec,
        "overshoot_percent": round_float(max(0.0, (max_temp - setpoint) / step_change * 100.0)),
        "settling_time_sec": settling_time_sec,
        "max_valve_percent": round_float(max(point["valve_percent"] for point in trajectory)),
        "saturation_ratio": round_float(saturated_samples / len(trajectory)),
    }


def is_feasible(metrics, case_data):
    acceptance = case_data["acceptance"]
    if metrics["rise_time_sec"] is None or metrics["settling_time_sec"] is None:
        return False
    return (
        metrics["rise_time_sec"] <= acceptance["max_rise_time_sec"]
        and metrics["overshoot_percent"] <= acceptance["max_overshoot_percent"]
        and metrics["settling_time_sec"] <= acceptance["max_settling_time_sec"]
        and metrics["saturation_ratio"] <= acceptance["max_saturation_ratio"]
    )


def evaluate_candidates(case_data):
    evaluations = []
    for lambda_sec in case_data["candidate_lambda_sec"]:
        gains = calculate_pi_gains(case_data["process"]["K"], case_data["process"]["tau_sec"], lambda_sec)
        trajectory = simulate_closed_loop(case_data, lambda_sec)
        metrics = compute_metrics(trajectory, case_data)
        evaluations.append(
            {
                "lambda_sec": round_float(lambda_sec),
                "controller": gains,
                "metrics": metrics,
                "feasible": is_feasible(metrics, case_data),
                "trajectory": trajectory,
            }
        )
    return evaluations


def main():
    case_data = load_case()
    evaluations = evaluate_candidates(case_data)
    summary = [
        {
            "lambda_sec": item["lambda_sec"],
            "controller": item["controller"],
            "metrics": item["metrics"],
            "feasible": item["feasible"],
        }
        for item in evaluations
    ]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
