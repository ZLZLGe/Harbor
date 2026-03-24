#!/bin/bash
set -euo pipefail

python3 <<'PY'
import math
import os

import numpy as np
import pandas as pd


OUTPUT_PATH = "/root/output/salinity_intrusion_driver.csv"


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
    return float(2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))))


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


transects = pd.read_csv("/root/data/salinity_transects.csv")
drivers = pd.read_csv("/root/data/estuary_driver_conditions.csv")

salt_front = (
    transects.loc[transects["salinity_psu"] >= 1.0]
    .groupby(["year", "survey_id"], as_index=False)["distance_km"]
    .max()
    .rename(columns={"distance_km": "salt_front_km"})
)

annual_intrusion = (
    salt_front.groupby("year", as_index=False)["salt_front_km"]
    .median()
    .rename(columns={"salt_front_km": "intrusion_severity_km"})
)

slope = sen_slope(
    annual_intrusion["year"].to_numpy(),
    annual_intrusion["intrusion_severity_km"].to_numpy(),
)
p_value = mann_kendall_p(annual_intrusion["intrusion_severity_km"].to_numpy())
intrusion_status = "worsening" if slope > 0 and p_value < 0.05 else "not_worsening"

merged = annual_intrusion.merge(drivers, on="year")
merged["net_radiation_wm2"] = merged["shortwave_wm2"] + merged["longwave_wm2"]

group_map = {
    "Heat": ["air_temp_c", "sea_surface_temp_c", "net_radiation_wm2"],
    "Flow": ["river_discharge_m3s", "dry_season_rain_mm", "tidal_prism_index"],
    "Wind": ["along_estuary_wind_ms", "mean_pressure_hpa"],
    "Human": ["channel_dredging_m3", "freshwater_withdrawal_mcm"],
}

for category, columns in group_map.items():
    merged[category] = pd.concat([zscore(merged[column]) for column in columns], axis=1).median(axis=1)

y = zscore(merged["intrusion_severity_km"]).to_numpy()
categories = ["Heat", "Flow", "Wind", "Human"]
X_full = np.column_stack([np.ones(len(merged)), merged[categories].to_numpy()])
coef_full = np.linalg.lstsq(X_full, y, rcond=None)[0]
sse_full = float(np.sum((y - X_full.dot(coef_full)) ** 2))

raw_scores = []
for category in categories:
    reduced_categories = [name for name in categories if name != category]
    X_reduced = np.column_stack([np.ones(len(merged)), merged[reduced_categories].to_numpy()])
    coef_reduced = np.linalg.lstsq(X_reduced, y, rcond=None)[0]
    sse_reduced = float(np.sum((y - X_reduced.dot(coef_reduced)) ** 2))
    raw_scores.append(max(0.0, sse_reduced - sse_full))

contributions = np.array(raw_scores, dtype=float)
contributions = contributions / contributions.sum() * 100
dominant_index = int(np.argmax(contributions))

result = pd.DataFrame(
    [
        {
            "intrusion_status": intrusion_status,
            "sen_slope_km_per_year": round(slope, 4),
            "dominant_category": categories[dominant_index],
            "contribution_pct": round(float(contributions[dominant_index]), 4),
        }
    ]
)

os.makedirs("/root/output", exist_ok=True)
result.to_csv(OUTPUT_PATH, index=False)
PY
