from pathlib import Path

import pandas as pd
import yaml


def task_root():
    root = Path("/root")
    try:
        if (root / "pressure_review.yaml").exists():
            return root
    except PermissionError:
        pass
    return Path(__file__).resolve().parents[1]


ROOT = task_root()
INPUT_ROOT = ROOT if (ROOT / "pressure_review.yaml").exists() else ROOT / "environment"
CONFIG_PATH = INPUT_ROOT / "pressure_review.yaml"
LOGS_DIR = INPUT_ROOT / "pressure_runs"
OUTPUT_PATH = ROOT / "pressure_surge_metrics.csv"


def round2(value):
    return round(float(value), 2)


def in_window(df, bounds):
    start, end = bounds
    return df[(df["time_s"] >= start) & (df["time_s"] <= end)].reset_index(drop=True)


def compute_expected():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    rows = []
    for candidate in config["candidates"]:
        df = pd.read_csv(LOGS_DIR / f"{candidate}.csv")
        evaluation = in_window(df, config["evaluation_window_s"])
        dip_window = in_window(df, config["dip_search_window_s"])
        steady = in_window(df, config["steady_state_window_s"])

        dip_index = dip_window["discharge_pressure_bar"].idxmin()
        minimum_pressure = float(dip_window.loc[dip_index, "discharge_pressure_bar"])
        minimum_time = float(dip_window.loc[dip_index, "time_s"])
        recovery = evaluation[evaluation["time_s"] >= minimum_time].reset_index(drop=True)
        recovery_span = float(config["target_pressure_bar"]) - minimum_pressure

        t10 = float(
            recovery[
                recovery["discharge_pressure_bar"] >= minimum_pressure + 0.1 * recovery_span
            ]["time_s"].iloc[0]
        )
        t90 = float(
            recovery[
                recovery["discharge_pressure_bar"] >= minimum_pressure + 0.9 * recovery_span
            ]["time_s"].iloc[0]
        )

        rise_time = round2(t90 - t10)
        overshoot = round2(
            max(
                0.0,
                (float(evaluation["discharge_pressure_bar"].max()) - float(config["target_pressure_bar"]))
                / float(config["target_pressure_bar"])
                * 100.0,
            )
        )
        steady_state_error = round2(
            abs(float(steady["discharge_pressure_bar"].mean()) - float(config["target_pressure_bar"]))
        )
        low_pressure_duration = round2(
            float((evaluation["discharge_pressure_bar"] < float(config["low_pressure_threshold_bar"])).sum())
            * float(config["sample_period_s"])
        )

        pass_count = sum(
            [
                rise_time <= float(config["limits"]["rise_time_s_max"]),
                overshoot <= float(config["limits"]["overshoot_pct_max"]),
                steady_state_error <= float(config["limits"]["steady_state_error_bar_max"]),
                low_pressure_duration <= float(config["limits"]["low_pressure_duration_s_max"]),
            ]
        )

        rows.append(
            {
                "candidate": candidate,
                "rise_time_s": rise_time,
                "overshoot_pct": overshoot,
                "steady_state_error_bar": steady_state_error,
                "low_pressure_duration_s": low_pressure_duration,
                "thresholds_passed": f"{int(pass_count)}/4",
                "_pass_count": int(pass_count),
            }
        )

    rows.sort(
        key=lambda row: (
            -row["_pass_count"],
            row["low_pressure_duration_s"],
            row["steady_state_error_bar"],
            row["overshoot_pct"],
            row["candidate"],
        )
    )

    expected = []
    for rank, row in enumerate(rows, start=1):
        expected.append(
            {
                "rank": rank,
                "candidate": row["candidate"],
                "rise_time_s": row["rise_time_s"],
                "overshoot_pct": row["overshoot_pct"],
                "steady_state_error_bar": row["steady_state_error_bar"],
                "low_pressure_duration_s": row["low_pressure_duration_s"],
                "thresholds_passed": row["thresholds_passed"],
            }
        )
    return expected


def test_assets_present():
    assert CONFIG_PATH.exists(), "pressure_review.yaml is missing"
    assert OUTPUT_PATH.exists(), "pressure_surge_metrics.csv is missing"

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert config["candidates"] == [
        "legacy_valve_trim",
        "balanced_vfd_pid",
        "buffer_tank_assist",
    ]

    for candidate in config["candidates"]:
        csv_path = LOGS_DIR / f"{candidate}.csv"
        assert csv_path.exists(), f"{csv_path.name} is missing"
        df = pd.read_csv(csv_path)
        assert len(df) == 121
        assert list(df.columns) == [
            "time_s",
            "demand_lps",
            "discharge_pressure_bar",
            "pump_speed_pct",
            "bypass_valve_pct",
        ]


def test_output_structure():
    output = pd.read_csv(OUTPUT_PATH)
    assert list(output.columns) == [
        "rank",
        "candidate",
        "rise_time_s",
        "overshoot_pct",
        "steady_state_error_bar",
        "low_pressure_duration_s",
        "thresholds_passed",
    ]
    assert output["rank"].tolist() == [1, 2, 3]


def test_output_matches_expected_metrics():
    actual = pd.read_csv(OUTPUT_PATH)
    expected = pd.DataFrame(compute_expected())

    assert actual.to_dict(orient="records") == expected.to_dict(orient="records")


def test_expected_ranking_profile():
    output = pd.read_csv(OUTPUT_PATH)

    assert output.iloc[0].to_dict() == {
        "rank": 1,
        "candidate": "balanced_vfd_pid",
        "rise_time_s": 6.0,
        "overshoot_pct": 0.8,
        "steady_state_error_bar": 0.01,
        "low_pressure_duration_s": 4.5,
        "thresholds_passed": "4/4",
    }
    assert output.iloc[1]["candidate"] == "buffer_tank_assist"
    assert output.iloc[1]["thresholds_passed"] == "3/4"
    assert output.iloc[2]["candidate"] == "legacy_valve_trim"
    assert output.iloc[2]["overshoot_pct"] == 6.4
