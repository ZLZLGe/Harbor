#!/bin/bash
set -euo pipefail

python3 <<'PY'
import math
import os

import numpy as np
import pandas as pd


def sen_slope(x: np.ndarray, y: np.ndarray) -> float:
    slopes = []
    for i in range(len(y) - 1):
        for j in range(i + 1, len(y)):
            slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    return float(np.median(slopes))


def mann_kendall_p(y: np.ndarray) -> float:
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


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


data = pd.read_csv("/root/data/reservoir_monthly_monitoring.csv")

annual = data.groupby("year", as_index=False).mean(numeric_only=True)
annual["net_radiation_wm2"] = annual["shortwave_wm2"] + annual["longwave_wm2"]

years = annual["year"].to_numpy()
evap = annual["evaporation_mm_day"].to_numpy()

slope = sen_slope(years, evap)
p_value = mann_kendall_p(evap)
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

summary = pd.DataFrame(
    [
        {
            "trend_label": trend_label,
            "sen_slope_mm_day_per_year": round(slope, 4),
            "p_value": round(p_value, 4),
            "dominant_category": categories[dominant_index],
            "contribution_pct": round(float(contributions[dominant_index]), 4),
        }
    ]
)

os.makedirs("/root/output", exist_ok=True)
summary.to_csv("/root/output/evaporation_driver_summary.csv", index=False)
PY
