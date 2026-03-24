#!/bin/bash
set -euo pipefail

python3 <<'PY'
import os

import numpy as np
import pandas as pd


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


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

output = pd.DataFrame(
    [
        {
            "dominant_category": categories[dominant_index],
            "contribution_pct": round(float(contributions[dominant_index]), 4),
        }
    ]
)

os.makedirs("/root/output", exist_ok=True)
output.to_csv("/root/output/snowmelt_peak_driver.csv", index=False)
PY
