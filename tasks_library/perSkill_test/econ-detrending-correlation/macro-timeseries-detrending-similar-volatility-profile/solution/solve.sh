#!/bin/bash
set -e

python3 <<'PY'
import os
import numpy as np
import pandas as pd
from pathlib import Path


def hp_cycle(values, lamb=1600.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def find_data_path():
    local_path = Path("environment/us_macro_quarterly_real_panel.csv")
    if local_path.exists():
        return local_path
    return Path("/root/us_macro_quarterly_real_panel.csv")


def find_output_path():
    override_dir = os.environ.get("HARBOR_OUTPUT_DIR")
    if override_dir:
        return Path(override_dir) / "cycle_volatility_profile.csv"
    return Path("/root/cycle_volatility_profile.csv")


code_to_label = {
    "RGDP": "GDP",
    "RPCE": "Consumption",
    "RPFI": "Fixed Investment",
}

data = pd.read_csv(find_data_path())
target = data[data["series_code"].isin(code_to_label)].copy()
target = target[target["quarter"].between("1990Q1", "2024Q4")]

rows = []
gdp_std = None
for code in ["RGDP", "RPCE", "RPFI"]:
    series = (
        target[target["series_code"] == code]
        .sort_values("quarter")["value"]
        .astype(float)
        .to_numpy()
    )
    cycle = hp_cycle(np.log(series), lamb=1600.0)
    cycle_std = float(np.std(cycle, ddof=1))
    if code == "RGDP":
        gdp_std = cycle_std
    rows.append(
        {
            "series": code_to_label[code],
            "series_code": code,
            "cycle_std": cycle_std,
        }
    )

for row in rows:
    row["relative_volatility_to_gdp"] = row["cycle_std"] / gdp_std

result = pd.DataFrame(rows).sort_values(
    "relative_volatility_to_gdp", ascending=False
)
result["cycle_std"] = result["cycle_std"].map(lambda x: f"{x:.6f}")
result["relative_volatility_to_gdp"] = result[
    "relative_volatility_to_gdp"
].map(lambda x: f"{x:.6f}")

result.to_csv(find_output_path(), index=False)
PY
