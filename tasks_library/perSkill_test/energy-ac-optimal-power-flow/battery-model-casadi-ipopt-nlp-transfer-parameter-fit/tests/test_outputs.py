#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys

OUTPUT_FILE = "/root/battery_model_fit_report.json"
CASE_FILE = "/root/battery_experiment_case.json"
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
STATUS_OK = {"optimal", "Solve_Succeeded", "Solved_To_Acceptable_Level"}
METRIC_TOL = 1e-9


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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


def assert_close(actual: float, expected: float, label: str, tol: float = METRIC_TOL) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tol):
        fail(f"{label} mismatch: expected {expected}, got {actual}")


def main() -> None:
    case = load_json(CASE_FILE)
    report = load_json(OUTPUT_FILE)

    for key in [
        "summary",
        "identified_parameters",
        "parameter_bound_margins",
        "residual_statistics",
        "train_segments",
        "validation_segments",
        "largest_residuals",
    ]:
        if key not in report:
            fail(f"missing top-level key: {key}")

    summary = report["summary"]
    if summary.get("scenario_id") != case["scenario_id"]:
        fail("scenario_id mismatch")
    if summary.get("solver_status") not in STATUS_OK:
        fail("solver_status is not acceptable")

    params = report["identified_parameters"]
    if set(params.keys()) != set(PARAMETER_NAMES):
        fail("identified_parameters keys do not match required parameter set")

    for name in PARAMETER_NAMES:
        if name not in params:
            fail(f"missing parameter: {name}")
        value = float(params[name])
        lo, hi = case["parameter_bounds"][name]
        if value < float(lo) or value > float(hi):
            fail(f"parameter {name} violates bounds")

    bound_rows = report["parameter_bound_margins"]
    if len(bound_rows) != len(PARAMETER_NAMES):
        fail("parameter_bound_margins length mismatch")
    for expected_name, row in zip(PARAMETER_NAMES, bound_rows):
        if row.get("name") != expected_name:
            fail("parameter_bound_margins order mismatch")
        value = float(params[expected_name])
        lo, hi = case["parameter_bounds"][expected_name]
        lower_margin = value - float(lo)
        upper_margin = float(hi) - value
        relative_margin = min(lower_margin, upper_margin) / (float(hi) - float(lo))
        assert_close(float(row["value"]), value, f"{expected_name} value")
        assert_close(float(row["lower_margin"]), lower_margin, f"{expected_name} lower_margin")
        assert_close(float(row["upper_margin"]), upper_margin, f"{expected_name} upper_margin")
        assert_close(float(row["relative_margin"]), relative_margin, f"{expected_name} relative_margin")

    tref = float(case["cell"]["reference_temperature_c"])
    train_records = []
    validation_records = []
    train_residuals = []
    validation_residuals = []
    all_points = []

    for segment in case["segments"]:
        points, final_v_rc = simulate_segment(segment["rows"], params, tref)
        residuals = [point["residual_v"] for point in points]
        record = {
            "segment_id": segment["segment_id"],
            "sample_count": len(points),
            "rmse_v": math.sqrt(sum(r * r for r in residuals) / len(residuals)),
            "mae_v": sum(abs(r) for r in residuals) / len(residuals),
            "max_abs_residual_v": max(abs(r) for r in residuals),
        }
        if segment["split"] == "train":
            record["final_rc_voltage_v"] = final_v_rc
            train_records.append(record)
            train_residuals.extend(residuals)
        else:
            record["mean_bias_v"] = sum(residuals) / len(residuals)
            validation_records.append(record)
            validation_residuals.extend(residuals)
        for point in points:
            all_points.append({"segment_id": segment["segment_id"], **point})

    if [row["segment_id"] for row in report["train_segments"]] != case["report_requirements"]["train_segment_ids"]:
        fail("train_segments order mismatch")
    if [row["segment_id"] for row in report["validation_segments"]] != case["report_requirements"]["validation_segment_ids"]:
        fail("validation_segments order mismatch")

    if len(report["train_segments"]) != len(train_records):
        fail("train_segments length mismatch")
    if len(report["validation_segments"]) != len(validation_records):
        fail("validation_segments length mismatch")

    for actual, expected in zip(report["train_segments"], train_records):
        if actual["segment_id"] != expected["segment_id"]:
            fail("train segment id mismatch")
        if int(actual["sample_count"]) != expected["sample_count"]:
            fail("train sample_count mismatch")
        assert_close(float(actual["rmse_v"]), expected["rmse_v"], f"{expected['segment_id']} rmse")
        assert_close(float(actual["mae_v"]), expected["mae_v"], f"{expected['segment_id']} mae")
        assert_close(
            float(actual["max_abs_residual_v"]),
            expected["max_abs_residual_v"],
            f"{expected['segment_id']} max_abs_residual",
        )
        assert_close(
            float(actual["final_rc_voltage_v"]),
            expected["final_rc_voltage_v"],
            f"{expected['segment_id']} final_rc_voltage",
        )

    for actual, expected in zip(report["validation_segments"], validation_records):
        if actual["segment_id"] != expected["segment_id"]:
            fail("validation segment id mismatch")
        if int(actual["sample_count"]) != expected["sample_count"]:
            fail("validation sample_count mismatch")
        assert_close(float(actual["rmse_v"]), expected["rmse_v"], f"{expected['segment_id']} rmse")
        assert_close(float(actual["mae_v"]), expected["mae_v"], f"{expected['segment_id']} mae")
        assert_close(
            float(actual["max_abs_residual_v"]),
            expected["max_abs_residual_v"],
            f"{expected['segment_id']} max_abs_residual",
        )
        assert_close(float(actual["mean_bias_v"]), expected["mean_bias_v"], f"{expected['segment_id']} mean_bias")

    train_sse = sum(r * r for r in train_residuals)
    validation_sse = sum(r * r for r in validation_residuals)
    assert_close(float(summary["objective_value_v2"]), train_sse, "objective_value_v2")
    if int(summary["train_sample_count"]) != len(train_residuals):
        fail("train_sample_count mismatch")
    if int(summary["validation_sample_count"]) != len(validation_residuals):
        fail("validation_sample_count mismatch")
    assert_close(float(summary["train_rmse_v"]), math.sqrt(train_sse / len(train_residuals)), "train_rmse_v")
    assert_close(
        float(summary["validation_rmse_v"]),
        math.sqrt(validation_sse / len(validation_residuals)),
        "validation_rmse_v",
    )
    assert_close(
        float(summary["max_abs_residual_v"]),
        max(max(abs(r) for r in train_residuals), max(abs(r) for r in validation_residuals)),
        "max_abs_residual_v",
    )
    expected_min_margin = min(float(row["relative_margin"]) for row in bound_rows)
    assert_close(float(summary["minimum_relative_bound_margin"]), expected_min_margin, "minimum_relative_bound_margin")

    residual_stats = report["residual_statistics"]
    assert_close(
        float(residual_stats["train_mae_v"]),
        sum(abs(r) for r in train_residuals) / len(train_residuals),
        "train_mae_v",
    )
    assert_close(
        float(residual_stats["train_mean_bias_v"]),
        sum(train_residuals) / len(train_residuals),
        "train_mean_bias_v",
    )
    assert_close(
        float(residual_stats["validation_mae_v"]),
        sum(abs(r) for r in validation_residuals) / len(validation_residuals),
        "validation_mae_v",
    )
    assert_close(
        float(residual_stats["validation_mean_bias_v"]),
        sum(validation_residuals) / len(validation_residuals),
        "validation_mean_bias_v",
    )

    if float(summary["train_rmse_v"]) >= 0.003:
        fail("train RMSE is too large")
    if float(summary["validation_rmse_v"]) >= 0.004:
        fail("validation RMSE is too large")
    if float(summary["max_abs_residual_v"]) >= 0.007:
        fail("max residual is too large")
    if float(summary["minimum_relative_bound_margin"]) <= 0.01:
        fail("solution sits too close to parameter bounds")

    expected_count = int(case["report_requirements"]["top_residual_count"])
    residual_rows = report["largest_residuals"]
    if len(residual_rows) != expected_count:
        fail("largest_residuals length mismatch")

    all_points.sort(key=lambda item: (-item["abs_residual_v"], item["segment_id"], item["step"]))
    expected_top = all_points[:expected_count]
    for rank, (actual, expected) in enumerate(zip(residual_rows, expected_top), start=1):
        if int(actual["rank"]) != rank:
            fail("largest_residuals rank mismatch")
        if actual["segment_id"] != expected["segment_id"]:
            fail("largest_residuals segment mismatch")
        if int(actual["step"]) != int(expected["step"]):
            fail("largest_residuals step mismatch")
        assert_close(float(actual["time_s"]), expected["time_s"], f"largest_residuals[{rank}].time_s")
        assert_close(float(actual["residual_v"]), expected["residual_v"], f"largest_residuals[{rank}].residual_v")
        assert_close(
            float(actual["abs_residual_v"]),
            expected["abs_residual_v"],
            f"largest_residuals[{rank}].abs_residual_v",
        )
        assert_close(
            float(actual["measured_voltage_v"]),
            expected["measured_voltage_v"],
            f"largest_residuals[{rank}].measured_voltage_v",
        )
        assert_close(
            float(actual["modeled_voltage_v"]),
            expected["modeled_voltage_v"],
            f"largest_residuals[{rank}].modeled_voltage_v",
        )
        assert_close(
            float(actual["temperature_c"]),
            expected["temperature_c"],
            f"largest_residuals[{rank}].temperature_c",
        )
        assert_close(float(actual["current_a"]), expected["current_a"], f"largest_residuals[{rank}].current_a")

    print("battery_model_fit_report.json validation passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
