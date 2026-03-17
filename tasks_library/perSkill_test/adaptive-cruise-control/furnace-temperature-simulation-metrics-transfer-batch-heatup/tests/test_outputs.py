from pathlib import Path

import pandas as pd
import yaml


ROOT = Path("/root")
RUNS_PATH = ROOT / "furnace_temperature_runs.csv"
SPEC_PATH = ROOT / "furnace_benchmark.yaml"
METRICS_PATH = ROOT / "furnace_metrics.csv"
REPORT_PATH = ROOT / "furnace_temperature_report.md"


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
    target_temperature = spec["target_temperature_c"]
    heatup_spec = spec["phases"]["heatup"]
    recovery_spec = spec["phases"]["recovery"]
    gates = spec["gates"]
    normalizers = spec["score_normalizers"]

    rows = []
    for configuration_id, group in runs.groupby("configuration_id"):
        group = group.sort_values("time_min")
        heatup = group[
            (group["time_min"] >= heatup_spec["start_time_min"])
            & (group["time_min"] <= heatup_spec["end_time_min"])
        ]
        recovery = group[
            (group["time_min"] >= recovery_spec["start_time_min"])
            & (group["time_min"] <= recovery_spec["end_time_min"])
        ]

        recovery_floor = recovery["temperature_c"].min()
        recovery_target = target_temperature - recovery_floor
        recovery_progress = recovery["temperature_c"] - recovery_floor
        recovery_times = recovery["time_min"] - recovery_spec["start_time_min"]

        raw_row = {
            "heatup_rise_time_min": rise_time(
                heatup["time_min"].tolist(),
                heatup["temperature_c"].tolist(),
                target_temperature,
            ),
            "heatup_overshoot_pct": overshoot_percent(
                heatup["temperature_c"].tolist(),
                target_temperature,
            ),
            "heatup_steady_state_error_c": steady_state_error(
                heatup["temperature_c"].tolist(),
                target_temperature,
            ),
            "heatup_settling_time_min": settling_time(
                heatup["time_min"].tolist(),
                heatup["temperature_c"].tolist(),
                target_temperature,
                heatup_spec["settling_tolerance"],
            ),
            "recovery_floor_c": recovery_floor,
            "recovery_rise_time_min": rise_time(
                recovery_times.tolist(),
                recovery_progress.tolist(),
                recovery_target,
            ),
            "recovery_overshoot_pct": overshoot_percent(
                recovery_progress.tolist(),
                recovery_target,
            ),
            "recovery_steady_state_error_c": steady_state_error(
                recovery_progress.tolist(),
                recovery_target,
            ),
            "recovery_settling_time_min": settling_time(
                recovery_times.tolist(),
                recovery_progress.tolist(),
                recovery_target,
                recovery_spec["settling_tolerance"],
            ),
        }

        row = {"configuration_id": configuration_id}
        for key, value in raw_row.items():
            row[key] = round(value, 3)

        passes_all_gates = (
            raw_row["heatup_rise_time_min"] <= gates["heatup_rise_time_max_min"]
            and raw_row["heatup_overshoot_pct"] <= gates["heatup_overshoot_max_pct"]
            and raw_row["heatup_steady_state_error_c"] <= gates["heatup_steady_state_error_max_c"]
            and raw_row["heatup_settling_time_min"] <= gates["heatup_settling_time_max_min"]
            and raw_row["recovery_floor_c"] >= gates["recovery_floor_min_c"]
            and raw_row["recovery_rise_time_min"] <= gates["recovery_rise_time_max_min"]
            and raw_row["recovery_overshoot_pct"] <= gates["recovery_overshoot_max_pct"]
            and raw_row["recovery_steady_state_error_c"] <= gates["recovery_steady_state_error_max_c"]
            and raw_row["recovery_settling_time_min"] <= gates["recovery_settling_time_max_min"]
        )
        row["passes_all_gates"] = "true" if passes_all_gates else "false"
        row["overall_score"] = round(
            raw_row["heatup_rise_time_min"] / normalizers["heatup_rise_time_min"]
            + raw_row["heatup_overshoot_pct"] / normalizers["heatup_overshoot_pct"]
            + raw_row["heatup_steady_state_error_c"] / normalizers["heatup_steady_state_error_c"]
            + raw_row["heatup_settling_time_min"] / normalizers["heatup_settling_time_min"]
            + raw_row["recovery_rise_time_min"] / normalizers["recovery_rise_time_min"]
            + raw_row["recovery_overshoot_pct"] / normalizers["recovery_overshoot_pct"]
            + raw_row["recovery_steady_state_error_c"] / normalizers["recovery_steady_state_error_c"]
            + raw_row["recovery_settling_time_min"] / normalizers["recovery_settling_time_min"],
            3,
        )
        rows.append(row)

    best = min(
        [row for row in rows if row["passes_all_gates"] == "true"],
        key=lambda item: item["overall_score"],
    )["configuration_id"]
    for row in rows:
        row["recommended"] = "true" if row["configuration_id"] == best else "false"

    return {row["configuration_id"]: row for row in rows}


def test_input_assets_present():
    assert RUNS_PATH.exists(), "furnace_temperature_runs.csv is missing"
    assert SPEC_PATH.exists(), "furnace_benchmark.yaml is missing"


def test_input_data_shape():
    runs = pd.read_csv(RUNS_PATH)
    assert list(runs.columns) == ["configuration_id", "time_min", "temperature_c"]
    assert len(runs) == 284
    assert sorted(runs["configuration_id"].unique().tolist()) == [
        "A_soak_guard",
        "B_fast_ramp",
        "C_balanced",
        "D_slow_trim",
    ]


def test_metrics_file_matches_expected_values():
    assert METRICS_PATH.exists(), "furnace_metrics.csv is missing"
    metrics = pd.read_csv(METRICS_PATH, dtype={"passes_all_gates": str, "recommended": str})
    expected = expected_rows()

    expected_columns = [
        "configuration_id",
        "heatup_rise_time_min",
        "heatup_overshoot_pct",
        "heatup_steady_state_error_c",
        "heatup_settling_time_min",
        "recovery_floor_c",
        "recovery_rise_time_min",
        "recovery_overshoot_pct",
        "recovery_steady_state_error_c",
        "recovery_settling_time_min",
        "passes_all_gates",
        "overall_score",
        "recommended",
    ]
    assert list(metrics.columns) == expected_columns
    assert list(metrics["configuration_id"]) == sorted(expected.keys())

    for _, row in metrics.iterrows():
        target = expected[row["configuration_id"]]
        for column in expected_columns[1:10] + ["overall_score"]:
            assert abs(float(row[column]) - target[column]) <= 1e-3, f"Mismatch in {row['configuration_id']} {column}"
        assert str(row["passes_all_gates"]).lower() == target["passes_all_gates"]
        assert str(row["recommended"]).lower() == target["recommended"]


def test_recommendation_is_balanced_candidate():
    metrics = pd.read_csv(METRICS_PATH, dtype={"passes_all_gates": str, "recommended": str})
    recommended = metrics.loc[metrics["recommended"].str.lower() == "true", "configuration_id"].tolist()
    assert recommended == ["C_balanced"]


def test_report_contains_required_sections_and_rationale():
    assert REPORT_PATH.exists(), "furnace_temperature_report.md is missing"
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert report.startswith("# Industrial Furnace Temperature Report")
    assert "## Metric Method" in report
    assert "## Configuration Summary" in report
    assert "## Recommended Configuration" in report
    assert "C_balanced" in report
    assert "passes every gate" in report
    assert "A_soak_guard" in report
    assert "B_fast_ramp" in report
    assert "D_slow_trim" in report
    assert "| configuration_id |" in report
