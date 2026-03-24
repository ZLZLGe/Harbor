import csv
import os

import numpy as np
import pandas as pd


OUTPUT_PATH = "/root/output/methane_flux_driver.csv"


def sen_slope(x: np.ndarray, y: np.ndarray) -> float:
    slopes = []
    for i in range(len(y) - 1):
        for j in range(i + 1, len(y)):
            slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    return float(np.median(slopes))


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


def expected_result():
    campaigns = pd.read_csv("/root/data/methane_flux_campaigns.csv")
    hydroclimate = pd.read_csv("/root/data/peatland_hydroclimate.csv")
    management = pd.read_csv("/root/data/restoration_actions.csv")

    campaign_flux = (
        campaigns.assign(
            weighted_flux=lambda df: df["zone_area_frac"] * df["methane_flux_mg_m2_day"]
        )
        .groupby(["year", "campaign_id"], as_index=False)
        .agg(site_flux_mg_m2_day=("weighted_flux", "sum"))
    )

    yearly_flux = (
        campaign_flux.groupby("year", as_index=False)["site_flux_mg_m2_day"]
        .mean()
        .rename(columns={"site_flux_mg_m2_day": "methane_flux_mg_m2_day"})
    )

    merged = yearly_flux.merge(hydroclimate, on="year").merge(management, on="year")
    merged["net_radiation_wm2"] = merged["shortwave_wm2"] + merged["longwave_wm2"]

    group_map = {
        "Heat": ["soil_temp_5cm_c", "peat_temp_15cm_c", "net_radiation_wm2"],
        "Flow": ["water_table_anomaly_cm", "inundation_days", "catchment_inflow_mm"],
        "Wind": ["mean_wind_ms", "gust_hours"],
        "Human": ["ditch_blocks_installed", "rewetted_margin_ha"],
    }

    for category, columns in group_map.items():
        merged[category] = pd.concat([zscore(merged[column]) for column in columns], axis=1).median(axis=1)

    flux_increment = merged["methane_flux_mg_m2_day"].diff()
    raw_scores = {}
    for category in ["Heat", "Flow", "Wind", "Human"]:
        category_increment = merged[category].diff()
        aligned = pd.DataFrame(
            {
                "flux_increment": flux_increment,
                "category_increment": category_increment,
            }
        ).dropna()
        correlation = float(aligned["flux_increment"].corr(aligned["category_increment"]))
        raw_scores[category] = max(0.0, correlation) ** 2

    contributions = pd.Series(raw_scores, dtype=float)
    contributions = contributions / contributions.sum() * 100
    dominant_category = str(contributions.idxmax())

    return {
        "flux_trend": "increasing"
        if sen_slope(merged["year"].to_numpy(), merged["methane_flux_mg_m2_day"].to_numpy()) > 0
        else "not_increasing",
        "sen_slope_mg_m2_day_per_year": round(
            sen_slope(merged["year"].to_numpy(), merged["methane_flux_mg_m2_day"].to_numpy()),
            4,
        ),
        "dominant_category": dominant_category,
        "contribution_pct": round(float(contributions[dominant_category]), 4),
    }


class TestPeatlandMethaneFluxDriver:
    def test_output_exists_and_schema(self):
        assert os.path.exists(OUTPUT_PATH), "methane_flux_driver.csv not found"

        with open(OUTPUT_PATH, "r", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == [
                "flux_trend",
                "sen_slope_mg_m2_day_per_year",
                "dominant_category",
                "contribution_pct",
            ]
            rows = list(reader)

        assert len(rows) == 1, "output must contain exactly one data row"

    def test_output_matches_expected_result(self):
        expected = expected_result()

        with open(OUTPUT_PATH, "r", newline="") as handle:
            row = next(csv.DictReader(handle))

        assert row["flux_trend"] == expected["flux_trend"]
        assert row["dominant_category"] == expected["dominant_category"]
        assert abs(float(row["sen_slope_mg_m2_day_per_year"]) - expected["sen_slope_mg_m2_day_per_year"]) <= 1e-4
        assert abs(float(row["contribution_pct"]) - expected["contribution_pct"]) <= 1e-4

    def test_expected_driver_signal(self):
        with open(OUTPUT_PATH, "r", newline="") as handle:
            row = next(csv.DictReader(handle))

        assert row["flux_trend"] == "increasing"
        assert abs(float(row["sen_slope_mg_m2_day_per_year"]) - 1.6667) <= 1e-4
        assert row["dominant_category"] == "Flow"
        assert float(row["contribution_pct"]) > 80.0
