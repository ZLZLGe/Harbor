import csv
import math
import os

import numpy as np
import pandas as pd


OUTPUT_PATH = "/root/output/evaporation_driver_summary.csv"
DATA_PATH = "/root/data/reservoir_monthly_monitoring.csv"


def sen_slope(x, y):
    slopes = []
    for i in range(len(y) - 1):
        for j in range(i + 1, len(y)):
            slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    return float(np.median(slopes))


def mann_kendall_p(y):
    n = len(y)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += int(y[j] > y[i]) - int(y[j] < y[i])
    var_s = n * (n - 1) * (2 * n + 5) / 18
    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def zscore(series):
    return (series - series.mean()) / series.std(ddof=0)


def expected_summary():
    data = pd.read_csv(DATA_PATH)
    annual = data.groupby("year", as_index=False).mean(numeric_only=True)
    annual["net_radiation_wm2"] = annual["shortwave_wm2"] + annual["longwave_wm2"]

    slope = sen_slope(annual["year"].to_numpy(), annual["evaporation_mm_day"].to_numpy())
    p_value = mann_kendall_p(annual["evaporation_mm_day"].to_numpy())
    trend_label = "intensified" if slope > 0 and p_value < 0.05 else "not_intensified"

    group_map = {
        "Heat": ["air_temp_c", "net_radiation_wm2"],
        "Flow": ["inflow_mcm", "release_mcm"],
        "Wind": ["mean_wind_ms", "gust_speed_ms"],
        "Human": ["irrigation_withdrawal_mcm", "shoreline_developed_frac"],
    }

    for columns in group_map.values():
        for column in columns:
            annual[f"{column}_z"] = zscore(annual[column])

    for category, columns in group_map.items():
        annual[category] = annual[[f"{column}_z" for column in columns]].mean(axis=1)

    X = annual[["Heat", "Flow", "Wind", "Human"]].to_numpy()
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=0)
    y = zscore(annual["evaporation_mm_day"]).to_numpy()
    coefficients = np.linalg.lstsq(np.column_stack([np.ones(len(X)), X]), y, rcond=None)[0][1:]
    contributions = np.abs(coefficients) / np.abs(coefficients).sum() * 100
    categories = ["Heat", "Flow", "Wind", "Human"]
    dominant_index = int(np.argmax(contributions))

    return {
        "trend_label": trend_label,
        "sen_slope_mm_day_per_year": round(slope, 4),
        "p_value": round(p_value, 4),
        "dominant_category": categories[dominant_index],
        "contribution_pct": round(float(contributions[dominant_index]), 4),
    }


class TestReservoirEvaporationAttribution:
    def test_output_exists_and_schema(self):
        assert os.path.exists(OUTPUT_PATH), "evaporation_driver_summary.csv not found"

        with open(OUTPUT_PATH, "r", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == [
                "trend_label",
                "sen_slope_mm_day_per_year",
                "p_value",
                "dominant_category",
                "contribution_pct",
            ]
            rows = list(reader)

        assert len(rows) == 1, "output must contain exactly one data row"

    def test_summary_values(self):
        expected = expected_summary()

        with open(OUTPUT_PATH, "r", newline="") as handle:
            row = next(csv.DictReader(handle))

        assert row["trend_label"] == expected["trend_label"]
        assert row["dominant_category"] == expected["dominant_category"]
        assert abs(float(row["sen_slope_mm_day_per_year"]) - expected["sen_slope_mm_day_per_year"]) <= 1e-4
        assert abs(float(row["p_value"]) - expected["p_value"]) <= 1e-4
        assert abs(float(row["contribution_pct"]) - expected["contribution_pct"]) <= 1e-4

    def test_expected_signal_strength(self):
        with open(OUTPUT_PATH, "r", newline="") as handle:
            row = next(csv.DictReader(handle))

        assert row["trend_label"] == "intensified"
        assert row["dominant_category"] == "Heat"
        assert float(row["contribution_pct"]) > 50.0
