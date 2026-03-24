#!/usr/bin/env python3
"""Simulator helpers for the brine mixer concentration-control task."""

import json


def load_case(case_path):
    with open(case_path, "r", encoding="utf-8") as f:
        return json.load(f)


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def round_float(value):
    return round(float(value), 4)


def disturbance_active(case, time_s):
    return case["flush_start_s"] <= time_s < case["flush_end_s"]


def simulate_pi_controller(case_path, kp, ki):
    case = load_case(case_path)
    dt = case["dt_s"]
    steps = int(round(case["duration_s"] / dt))
    concentration = case["initial_concentration_pct"]
    integral = 0.0
    trace = []

    for step in range(steps + 1):
        time_s = round(step * dt, 10)
        active = disturbance_active(case, time_s)
        error = case["target_concentration_pct"] - concentration
        integral = clamp(
            integral + error * dt,
            case["integral_min"],
            case["integral_max"],
        )
        valve = clamp(
            case["nominal_brine_valve_pct"] + kp * error + ki * integral,
            case["valve_min_pct"],
            case["valve_max_pct"],
        )

        trace.append(
            {
                "time_s": round_float(time_s),
                "concentration_pct": round_float(concentration),
                "brine_valve_pct": round_float(valve),
                "dilution_active": active,
                "error_pct": round_float(error),
            }
        )

        equilibrium = (
            case["base_concentration_pct"]
            + case["process_gain_pct_per_valve_pct"] * valve
            - (case["dilution_shift_pct"] if active else 0.0)
        )
        concentration += (equilibrium - concentration) * dt / case["time_constant_s"]

    return trace


def build_sampled_response(trace, sample_times):
    by_time = {entry["time_s"]: entry for entry in trace}
    return [by_time[round_float(time_s)] for time_s in sample_times]


def _settling_time(trace, start_time, end_time, target, band):
    window = [entry for entry in trace if start_time <= entry["time_s"] <= end_time]
    for index, entry in enumerate(window):
        if abs(entry["concentration_pct"] - target) <= band:
            remainder = window[index:]
            if all(abs(item["concentration_pct"] - target) <= band for item in remainder):
                return round_float(entry["time_s"] - start_time)
    return round_float(end_time - start_time)


def compute_phase_summary(trace, case):
    target = case["target_concentration_pct"]
    startup_settling_time = _settling_time(
        trace,
        0.0,
        case["flush_start_s"] - case["dt_s"],
        target,
        case["settling_band_pct"],
    )
    flush_trace = [entry for entry in trace if entry["dilution_active"]]
    post_flush_recovery_time = _settling_time(
        trace,
        case["flush_end_s"],
        case["duration_s"],
        target,
        case["settling_band_pct"],
    )
    steady_state_entries = [
        entry
        for entry in trace
        if entry["time_s"] >= case["duration_s"] - case["steady_state_window_s"]
    ]
    average_concentration = sum(entry["concentration_pct"] for entry in steady_state_entries) / len(
        steady_state_entries
    )
    integral_absolute_error = sum(abs(entry["error_pct"]) * case["dt_s"] for entry in trace)

    return {
        "startup_settling_time_s": startup_settling_time,
        "flush_min_concentration_pct": round_float(
            min(entry["concentration_pct"] for entry in flush_trace)
        ),
        "post_flush_recovery_time_s": post_flush_recovery_time,
        "steady_state_error_pct": round_float(abs(average_concentration - target)),
        "integral_absolute_error_pct_s": round_float(integral_absolute_error),
        "max_brine_valve_pct": round_float(max(entry["brine_valve_pct"] for entry in trace)),
        "final_concentration_pct": round_float(trace[-1]["concentration_pct"]),
    }
