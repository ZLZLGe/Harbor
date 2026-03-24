import csv
import os

import numpy as np
import pandas as pd


OUTPUT_PATH = "/root/output/snowmelt_peak_driver.csv"


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


def expected_result():
    timing = pd.read_csv("/root/data/snowmelt_peak_timing.csv")
    energy = pd.read_csv("/root/data/snow_energy_balance.csv")
    hydrology = pd.read_csv("/root/data/basin_hydrology.csv")
    operations = pd.read_csv("/root/data/winter_operations.csv")

    merged = timing.merge(energy, on="year").merge(hydrology, on="year").merge(operations, on="year")
    merged["net_radiation_wm2"] = merged["shortwave_wm2"] + merged["longwave_wm2"]
    merged["peak_advance_days"] = merged["peak_doy"].max() - merged["peak_doy"]

    group_map = {
        "Heat": ["spring_air_temp_c", "net_radiation_wm2", "thawing_degree_days"],
        "Flow": ["spring_precip_mm", "rain_on_snow_days", "antecedent_runoff_mm"],
        "Wind": ["foehn_hours", "ridge_gust_ms"],
        "Human": ["snowmaking_withdrawal_mm", "trail_grooming_days"],
    }

    for category, columns in group_map.items():
        merged[category] = pd.concat([zscore(merged[column]) for column in columns], axis=1).mean(axis=1)

    X = merged[["Heat", "Flow", "Wind", "Human"]].to_numpy()
    X = np.column_stack([np.ones(len(X)), X])
    y = zscore(merged["peak_advance_days"]).to_numpy()

    coefficients = np.linalg.lstsq(X, y, rcond=None)[0][1:]
    positive_coefficients = np.clip(coefficients, 0.0, None)
    contributions = positive_coefficients / positive_coefficients.sum() * 100

    categories = ["Heat", "Flow", "Wind", "Human"]
    dominant_index = int(np.argmax(contributions))

    return {
        "dominant_category": categories[dominant_index],
        "contribution_pct": round(float(contributions[dominant_index]), 4),
    }


class TestSnowmeltPeakDriver:
    def test_output_exists_and_schema(self):
        assert os.path.exists(OUTPUT_PATH), "snowmelt_peak_driver.csv not found"

        with open(OUTPUT_PATH, "r", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == ["dominant_category", "contribution_pct"]
            rows = list(reader)

        assert len(rows) == 1, "output must contain exactly one data row"

    def test_output_matches_expected_result(self):
        expected = expected_result()

        with open(OUTPUT_PATH, "r", newline="") as handle:
            row = next(csv.DictReader(handle))

        assert row["dominant_category"] == expected["dominant_category"]
        assert abs(float(row["contribution_pct"]) - expected["contribution_pct"]) <= 1e-4

    def test_expected_signal_direction(self):
        with open(OUTPUT_PATH, "r", newline="") as handle:
            row = next(csv.DictReader(handle))

        assert row["dominant_category"] == "Wind"
        assert float(row["contribution_pct"]) > 60.0
