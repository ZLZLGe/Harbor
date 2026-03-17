from pathlib import Path

import pandas as pd
import yaml


ROOT = Path("/root")
RUNS_PATH = ROOT / "acc_calibration_runs.csv"
SPEC_PATH = ROOT / "benchmark_spec.yaml"
METRICS_PATH = ROOT / "calibration_metrics.csv"
REPORT_PATH = ROOT / "acc_calibration_benchmark.md"


def rise_time(times, values, target):
    t10 = None
    t90 = None
    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = float(t)
        if t90 is None and v >= 0.9 * target:
            t90 = float(t)
            break
    if t10 is None or t90 is None:
        return None
    return t90 - t10


def overshoot_percent(values, target):
    maximum = max(values)
    if maximum <= target:
        return 0.0
    return ((maximum - target) / target) * 100.0


def steady_state_error(values, target, final_fraction=0.1):
    start = int(len(values) * (1.0 - final_fraction))
    final_slice = values[start:]
    final_average = sum(final_slice) / len(final_slice)
    return abs(target - final_average)


def settling_time(times, values, target, tolerance):
    band = target * tolerance
    lower = target - band
    upper = target + band
    settled_at = None
    for t, v in zip(times, values):
        if v < lower or v > upper:
            settled_at = None
        elif settled_at is None:
            settled_at = float(t)
    return settled_at


def expected_rows():
    with SPEC_PATH.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)

    runs = pd.read_csv(RUNS_PATH)
    cruise_spec = spec["phases"]["cruise_accel"]
    recovery_spec = spec["phases"]["gap_recovery"]
    gates = spec["gates"]
    normalizers = spec["score_normalizers"]

    rows = []
    for calibration_id, group in runs.groupby("calibration_id"):
        group = group.sort_values("time_s")
        cruise = group[
            (group["time_s"] >= cruise_spec["start_time_s"])
            & (group["time_s"] <= cruise_spec["end_time_s"])
        ]
        recovery = group[
            (group["time_s"] >= recovery_spec["start_time_s"])
            & (group["time_s"] <= recovery_spec["end_time_s"])
        ]
        recovery_times = recovery["time_s"] - recovery_spec["start_time_s"]

        raw_row = {
            "cruise_rise_time_s": rise_time(
                cruise["time_s"].tolist(),
                cruise[cruise_spec["signal_column"]].tolist(),
                cruise_spec["target"],
            ),
            "cruise_overshoot_pct": overshoot_percent(
                cruise[cruise_spec["signal_column"]].tolist(),
                cruise_spec["target"],
            ),
            "cruise_steady_state_error_mps": steady_state_error(
                cruise[cruise_spec["signal_column"]].tolist(),
                cruise_spec["target"],
            ),
            "cruise_settling_time_s": settling_time(
                cruise["time_s"].tolist(),
                cruise[cruise_spec["signal_column"]].tolist(),
                cruise_spec["target"],
                cruise_spec["settling_tolerance"],
            ),
            "recovery_rise_time_s": rise_time(
                recovery_times.tolist(),
                recovery[recovery_spec["signal_column"]].tolist(),
                recovery_spec["target"],
            ),
            "recovery_overshoot_pct": overshoot_percent(
                recovery[recovery_spec["signal_column"]].tolist(),
                recovery_spec["target"],
            ),
            "recovery_steady_state_error_m": steady_state_error(
                recovery[recovery_spec["signal_column"]].tolist(),
                recovery_spec["target"],
            ),
            "recovery_settling_time_s": settling_time(
                recovery_times.tolist(),
                recovery[recovery_spec["signal_column"]].tolist(),
                recovery_spec["target"],
                recovery_spec["settling_tolerance"],
            ),
            "min_distance_m": pd.to_numeric(group["distance_m"], errors="coerce").min(),
        }

        row = {"calibration_id": calibration_id}
        for key, value in raw_row.items():
            row[key] = round(value, 3)

        passes_all_gates = (
            raw_row["cruise_rise_time_s"] <= gates["cruise_rise_time_max_s"]
            and raw_row["cruise_overshoot_pct"] <= gates["cruise_overshoot_max_pct"]
            and raw_row["cruise_steady_state_error_mps"] <= gates["cruise_steady_state_error_max_mps"]
            and raw_row["cruise_settling_time_s"] <= gates["cruise_settling_time_max_s"]
            and raw_row["recovery_rise_time_s"] <= gates["recovery_rise_time_max_s"]
            and raw_row["recovery_overshoot_pct"] <= gates["recovery_overshoot_max_pct"]
            and raw_row["recovery_steady_state_error_m"] <= gates["recovery_steady_state_error_max_m"]
            and raw_row["recovery_settling_time_s"] <= gates["recovery_settling_time_max_s"]
            and raw_row["min_distance_m"] >= gates["min_distance_min_m"]
        )
        row["passes_all_gates"] = "true" if passes_all_gates else "false"
        row["overall_score"] = round(
            raw_row["cruise_rise_time_s"] / normalizers["cruise_rise_time_s"]
            + raw_row["cruise_overshoot_pct"] / normalizers["cruise_overshoot_pct"]
            + raw_row["cruise_steady_state_error_mps"] / normalizers["cruise_steady_state_error_mps"]
            + raw_row["cruise_settling_time_s"] / normalizers["cruise_settling_time_s"]
            + raw_row["recovery_rise_time_s"] / normalizers["recovery_rise_time_s"]
            + raw_row["recovery_overshoot_pct"] / normalizers["recovery_overshoot_pct"]
            + raw_row["recovery_steady_state_error_m"] / normalizers["recovery_steady_state_error_m"]
            + raw_row["recovery_settling_time_s"] / normalizers["recovery_settling_time_s"],
            3,
        )
        rows.append(row)

    best = min(
        [row for row in rows if row["passes_all_gates"] == "true"],
        key=lambda item: item["overall_score"],
    )["calibration_id"]
    for row in rows:
        row["recommended"] = "true" if row["calibration_id"] == best else "false"

    return {row["calibration_id"]: row for row in rows}


def test_input_assets_present():
    assert RUNS_PATH.exists(), "acc_calibration_runs.csv is missing"
    assert SPEC_PATH.exists(), "benchmark_spec.yaml is missing"


def test_metrics_file_matches_expected_values():
    assert METRICS_PATH.exists(), "calibration_metrics.csv is missing"
    metrics = pd.read_csv(METRICS_PATH, dtype={"passes_all_gates": str, "recommended": str})
    expected = expected_rows()

    expected_columns = [
        "calibration_id",
        "cruise_rise_time_s",
        "cruise_overshoot_pct",
        "cruise_steady_state_error_mps",
        "cruise_settling_time_s",
        "recovery_rise_time_s",
        "recovery_overshoot_pct",
        "recovery_steady_state_error_m",
        "recovery_settling_time_s",
        "min_distance_m",
        "passes_all_gates",
        "overall_score",
        "recommended",
    ]
    assert list(metrics.columns) == expected_columns
    assert list(metrics["calibration_id"]) == sorted(expected.keys())

    for _, row in metrics.iterrows():
        target = expected[row["calibration_id"]]
        for column in expected_columns[1:10] + ["overall_score"]:
            assert abs(float(row[column]) - target[column]) <= 1e-3, f"Mismatch in {row['calibration_id']} {column}"
        assert str(row["passes_all_gates"]).lower() == target["passes_all_gates"]
        assert str(row["recommended"]).lower() == target["recommended"]


def test_recommendation_is_balanced_candidate():
    metrics = pd.read_csv(METRICS_PATH, dtype={"passes_all_gates": str, "recommended": str})
    recommended = metrics.loc[metrics["recommended"].str.lower() == "true", "calibration_id"].tolist()
    assert recommended == ["C_balanced"]


def test_report_contains_required_sections_and_rationale():
    assert REPORT_PATH.exists(), "acc_calibration_benchmark.md is missing"
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert report.startswith("# ACC Calibration Benchmark")
    assert "## Metric Method" in report
    assert "## Calibration Summary" in report
    assert "## Recommended Calibration" in report
    assert "C_balanced" in report
    assert "passes every gate" in report
    assert "A_comfort" in report
    assert "B_aggressive" in report
    assert "D_sluggish" in report
    assert "| calibration_id |" in report
