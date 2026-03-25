import tomllib

import numpy as np
import pandas as pd
import pytest
from netCDF4 import Dataset

CONFIG_PATH = "/root/config/refuge_rules.toml"
NC_PATH = "/root/data/blue_heron_output.nc"
REPORT_PATH = "/root/reports/refuge_thickness_daily.csv"


def load_config():
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def calculate_time_step_thicknesses(config: dict) -> pd.DataFrame:
    start_time = pd.Timestamp(config["simulation_start"])
    lake_depth_m = float(config["lake_depth_m"])

    with Dataset(NC_PATH, "r") as ds:
        time_values = np.array(ds.variables["time"][:], dtype=float)
        z = ds.variables["z"][:]
        temp = ds.variables["temp"][:]

    rows = []
    for time_index, hour_offset in enumerate(time_values):
        timestamp = start_time + pd.Timedelta(hours=float(hour_offset))
        frame = pd.DataFrame(
            {
                "depth_from_surface_m": lake_depth_m - np.asarray(z[time_index, :, 0, 0], dtype=float),
                "temp_c": np.asarray(temp[time_index, :, 0, 0], dtype=float),
            }
        )
        frame = frame.replace([np.inf, -np.inf], np.nan).dropna().sort_values("depth_from_surface_m").reset_index(drop=True)
        upper_bounds = [0.0]
        upper_bounds.extend(
            (frame["depth_from_surface_m"].iloc[i - 1] + frame["depth_from_surface_m"].iloc[i]) / 2.0
            for i in range(1, len(frame))
        )
        lower_bounds = [
            (frame["depth_from_surface_m"].iloc[i] + frame["depth_from_surface_m"].iloc[i + 1]) / 2.0
            for i in range(len(frame) - 1)
        ]
        lower_bounds.append(lake_depth_m)
        frame["layer_thickness_m"] = np.asarray(lower_bounds) - np.asarray(upper_bounds)

        rows.append(
            {
                "date": timestamp.date().isoformat(),
                "refuge_thickness_m": float(
                    frame.loc[
                        frame["temp_c"].between(
                            float(config["refuge_min_temp_c"]),
                            float(config["refuge_max_temp_c"]),
                            inclusive="both",
                        ),
                        "layer_thickness_m",
                    ].sum()
                ),
            }
        )

    return pd.DataFrame(rows)


def build_expected_daily(config: dict) -> pd.DataFrame:
    daily = (
        calculate_time_step_thicknesses(config)
        .groupby("date", as_index=False)["refuge_thickness_m"]
        .mean()
        .sort_values("date")
        .reset_index(drop=True)
    )

    daily["summer_minimum_flag"] = 0
    daily["first_collapse_flag"] = 0

    summer_mask = daily["date"].between(config["summer_start_date"], config["summer_end_date"])
    summer = daily.loc[summer_mask].reset_index()

    min_index = int(summer.loc[summer["refuge_thickness_m"].idxmin(), "index"])
    daily.loc[min_index, "summer_minimum_flag"] = 1

    collapse_rows = summer.loc[summer["refuge_thickness_m"] < float(config["collapse_threshold_m"])]
    if not collapse_rows.empty:
        first_collapse_index = int(collapse_rows.iloc[0]["index"])
        daily.loc[first_collapse_index, "first_collapse_flag"] = 1

    return daily[["date", "refuge_thickness_m", "summer_minimum_flag", "first_collapse_flag"]]


def test_report_exists_and_columns_match_contract():
    report = pd.read_csv(REPORT_PATH)
    assert list(report.columns) == [
        "date",
        "refuge_thickness_m",
        "summer_minimum_flag",
        "first_collapse_flag",
    ]
    assert report["date"].is_monotonic_increasing


def test_report_matches_expected_daily_values():
    config = load_config()
    expected = build_expected_daily(config)
    actual = pd.read_csv(REPORT_PATH)

    assert len(actual) == len(expected)
    assert actual["date"].tolist() == expected["date"].tolist()
    assert np.allclose(actual["refuge_thickness_m"], expected["refuge_thickness_m"], atol=5e-4)
    assert actual["summer_minimum_flag"].tolist() == expected["summer_minimum_flag"].tolist()
    assert actual["first_collapse_flag"].tolist() == expected["first_collapse_flag"].tolist()
    assert actual["summer_minimum_flag"].sum() == expected["summer_minimum_flag"].sum()
    assert actual["first_collapse_flag"].sum() == expected["first_collapse_flag"].sum()
