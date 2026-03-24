#!/bin/bash
set -euo pipefail

apt-get update -qq
apt-get install -y -qq libgfortran5 > /dev/null 2>&1
pip3 install --break-system-packages numpy==1.26.4 casadi==3.6.7 -q

python3 <<'PY'
from __future__ import annotations

import json
import math

import casadi as ca
import numpy as np

CASE_FILE = "/root/battery_experiment_case.json"
OUTPUT_FILE = "/root/battery_model_fit_report.json"
PARAMETER_NAMES = [
    "r0_ref_ohm",
    "r0_temp_coeff_per_c",
    "r1_ref_ohm",
    "r1_temp_coeff_per_c",
    "c1_ref_f",
    "c1_temp_coeff_per_c",
]
ROW_IDX = {
    "step": 0,
    "time_s": 1,
    "dt_s": 2,
    "current_a": 3,
    "temperature_c": 4,
    "soc": 5,
    "voltage_v": 6,
    "ocv_v": 7,
}


def build_solver(case: dict) -> tuple[ca.Function, list[float], list[float], ca.Function]:
    bounds = case["parameter_bounds"]
    lower = np.array([bounds[name][0] for name in PARAMETER_NAMES], dtype=float)
    upper = np.array([bounds[name][1] for name in PARAMETER_NAMES], dtype=float)
    span = upper - lower
    tref = float(case["cell"]["reference_temperature_c"])

    z = ca.MX.sym("z", len(PARAMETER_NAMES))
    theta = lower + span * z

    objective = ca.MX(0)
    for segment in case["segments"]:
        if segment["split"] != "train":
            continue
        v_rc = ca.MX(0)
        for row in segment["rows"]:
            dt = float(row[ROW_IDX["dt_s"]])
            current = float(row[ROW_IDX["current_a"]])
            temp_c = float(row[ROW_IDX["temperature_c"]])
            measured_v = float(row[ROW_IDX["voltage_v"]])
            ocv_v = float(row[ROW_IDX["ocv_v"]])

            r0 = theta[0] * ca.exp(theta[1] * (temp_c - tref))
            r1 = theta[2] * ca.exp(theta[3] * (temp_c - tref))
            c1 = theta[4] * ca.exp(theta[5] * (temp_c - tref))
            modeled_v = ocv_v - current * r0 - v_rc
            residual = modeled_v - measured_v
            objective += residual**2
            alpha = ca.exp(-dt / (r1 * c1))
            v_rc = alpha * v_rc + r1 * (1.0 - alpha) * current

    solver = ca.nlpsol(
        "solver",
        "ipopt",
        {"x": z, "f": objective},
        {
            "ipopt.print_level": 0,
            "ipopt.max_iter": 2000,
            "ipopt.tol": 1e-9,
            "ipopt.acceptable_tol": 1e-7,
            "ipopt.mu_strategy": "adaptive",
            "print_time": False,
        },
    )
    return solver, lower.tolist(), upper.tolist(), ca.Function("theta_fn", [z], [theta])


def scale_guess(guess: list[float], lower: list[float], upper: list[float]) -> list[float]:
    scaled = []
    for value, lo, hi in zip(guess, lower, upper):
        scaled.append((value - lo) / (hi - lo))
    return scaled


def simulate_segment(rows: list[list[float]], params: dict[str, float], tref: float) -> tuple[list[dict], float]:
    points = []
    v_rc = 0.0
    for row in rows:
        step = int(row[ROW_IDX["step"]])
        time_s = float(row[ROW_IDX["time_s"]])
        dt = float(row[ROW_IDX["dt_s"]])
        current = float(row[ROW_IDX["current_a"]])
        temp_c = float(row[ROW_IDX["temperature_c"]])
        measured_v = float(row[ROW_IDX["voltage_v"]])
        ocv_v = float(row[ROW_IDX["ocv_v"]])

        r0 = params["r0_ref_ohm"] * math.exp(params["r0_temp_coeff_per_c"] * (temp_c - tref))
        r1 = params["r1_ref_ohm"] * math.exp(params["r1_temp_coeff_per_c"] * (temp_c - tref))
        c1 = params["c1_ref_f"] * math.exp(params["c1_temp_coeff_per_c"] * (temp_c - tref))
        modeled_v = ocv_v - current * r0 - v_rc
        residual = modeled_v - measured_v
        points.append(
            {
                "step": step,
                "time_s": time_s,
                "residual_v": residual,
                "abs_residual_v": abs(residual),
                "measured_voltage_v": measured_v,
                "modeled_voltage_v": modeled_v,
                "temperature_c": temp_c,
                "current_a": current,
            }
        )
        alpha = math.exp(-dt / (r1 * c1))
        v_rc = alpha * v_rc + r1 * (1.0 - alpha) * current
    return points, v_rc


def main() -> None:
    with open(CASE_FILE, encoding="utf-8") as f:
        case = json.load(f)

    solver, lower, upper, theta_fn = build_solver(case)

    starts = [
        [0.5] * len(PARAMETER_NAMES),
        scale_guess([0.014, -0.01, 0.02, -0.015, 2400.0, 0.006], lower, upper),
        scale_guess([0.018, -0.006, 0.028, -0.01, 1800.0, 0.0], lower, upper),
        scale_guess([0.011, -0.02, 0.014, -0.026, 3300.0, 0.012], lower, upper),
    ]

    best = None
    best_status = None
    for start in starts:
        try:
            sol = solver(x0=start, lbx=[0.0] * len(PARAMETER_NAMES), ubx=[1.0] * len(PARAMETER_NAMES))
        except Exception:
            continue
        status = solver.stats().get("return_status", "")
        value = float(sol["f"])
        if best is None or value < float(best["f"]):
            best = sol
            best_status = status

    if best is None:
        raise RuntimeError("nonlinear least-squares solve failed from all initializations")

    theta = np.array(theta_fn(best["x"])).reshape(-1)
    params = {name: float(theta[i]) for i, name in enumerate(PARAMETER_NAMES)}
    tref = float(case["cell"]["reference_temperature_c"])

    train_segments = []
    validation_segments = []
    train_residuals = []
    validation_residuals = []
    all_points = []

    for segment in case["segments"]:
        points, final_v_rc = simulate_segment(segment["rows"], params, tref)
        residuals = [point["residual_v"] for point in points]
        record = {
            "segment_id": segment["segment_id"],
            "sample_count": len(points),
            "rmse_v": float(math.sqrt(sum(r * r for r in residuals) / len(residuals))),
            "mae_v": float(sum(abs(r) for r in residuals) / len(residuals)),
            "max_abs_residual_v": float(max(abs(r) for r in residuals)),
        }
        for point in points:
            all_points.append({"segment_id": segment["segment_id"], **point})
        if segment["split"] == "train":
            record["final_rc_voltage_v"] = float(final_v_rc)
            train_segments.append(record)
            train_residuals.extend(residuals)
        else:
            record["mean_bias_v"] = float(sum(residuals) / len(residuals))
            validation_segments.append(record)
            validation_residuals.extend(residuals)

    all_points.sort(key=lambda item: (-item["abs_residual_v"], item["segment_id"], item["step"]))
    largest_residuals = []
    for rank, point in enumerate(all_points[: int(case["report_requirements"]["top_residual_count"])], start=1):
        largest_residuals.append({"rank": rank, **point})

    parameter_bound_margins = []
    min_relative_margin = float("inf")
    for name in PARAMETER_NAMES:
        lo, hi = case["parameter_bounds"][name]
        value = params[name]
        lower_margin = value - float(lo)
        upper_margin = float(hi) - value
        relative_margin = min(lower_margin, upper_margin) / (float(hi) - float(lo))
        min_relative_margin = min(min_relative_margin, relative_margin)
        parameter_bound_margins.append(
            {
                "name": name,
                "value": value,
                "lower_margin": lower_margin,
                "upper_margin": upper_margin,
                "relative_margin": relative_margin,
            }
        )

    report = {
        "summary": {
            "scenario_id": case["scenario_id"],
            "solver_status": "optimal" if best_status in {"Solve_Succeeded", "Solved_To_Acceptable_Level"} else best_status,
            "objective_value_v2": float(sum(r * r for r in train_residuals)),
            "train_sample_count": len(train_residuals),
            "validation_sample_count": len(validation_residuals),
            "train_rmse_v": float(math.sqrt(sum(r * r for r in train_residuals) / len(train_residuals))),
            "validation_rmse_v": float(math.sqrt(sum(r * r for r in validation_residuals) / len(validation_residuals))),
            "max_abs_residual_v": float(
                max(max(abs(r) for r in train_residuals), max(abs(r) for r in validation_residuals))
            ),
            "minimum_relative_bound_margin": float(min_relative_margin),
        },
        "identified_parameters": params,
        "parameter_bound_margins": parameter_bound_margins,
        "residual_statistics": {
            "train_mae_v": float(sum(abs(r) for r in train_residuals) / len(train_residuals)),
            "train_mean_bias_v": float(sum(train_residuals) / len(train_residuals)),
            "validation_mae_v": float(sum(abs(r) for r in validation_residuals) / len(validation_residuals)),
            "validation_mean_bias_v": float(sum(validation_residuals) / len(validation_residuals)),
        },
        "train_segments": train_segments,
        "validation_segments": validation_segments,
        "largest_residuals": largest_residuals,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
PY
