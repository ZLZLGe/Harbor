#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd
from netCDF4 import Dataset

NML_PATH = "/root/config/glm3.nml"
NC_PATH = "/root/data/mendota_stratified_output.nc"
OBS_PATH = "/root/data/alignment_observations.csv"
REPORT_PATH = "/root/reports/temperature_alignment_report.json"
SURFACE_MAX_DEPTH = 5
DEEP_MIN_DEPTH = 15


def read_nml_value(text: str, key: str) -> str:
    match = re.search(rf"{key}\s*=\s*'([^']+)'", text)
    if match:
        return match.group(1)
    match = re.search(rf"{key}\s*=\s*([-+]?[0-9]*\.?[0-9]+)", text)
    if not match:
        raise ValueError(f"missing {key} in glm3.nml")
    return match.group(1)


def load_config():
    text = open(NML_PATH, "r", encoding="utf-8").read()
    start = pd.Timestamp(datetime.strptime(read_nml_value(text, "start"), "%Y-%m-%d %H:%M:%S"))
    lake_depth = float(read_nml_value(text, "lake_depth"))
    return start, lake_depth


def load_simulation(start: pd.Timestamp, lake_depth: float) -> pd.DataFrame:
    with Dataset(NC_PATH, "r") as ds:
        times = ds.variables["time"][:]
        z = ds.variables["z"][:]
        temp = ds.variables["temp"][:]

    records = []
    for t_idx, hour_offset in enumerate(times):
        dt = start + pd.Timedelta(hours=float(hour_offset))
        heights = z[t_idx, :, 0, 0]
        temps = temp[t_idx, :, 0, 0]
        for height, temp_value in zip(heights, temps):
            if np.ma.is_masked(height) or np.ma.is_masked(temp_value):
                continue
            rounded_depth = int(round(lake_depth - float(height)))
            if 0 <= rounded_depth <= lake_depth:
                records.append(
                    {
                        "datetime": dt,
                        "depth_rounded_m": rounded_depth,
                        "temp_sim": float(temp_value),
                    }
                )

    return (
        pd.DataFrame(records)
        .groupby(["datetime", "depth_rounded_m"], as_index=False)["temp_sim"]
        .mean()
    )


def load_observations() -> pd.DataFrame:
    obs = pd.read_csv(OBS_PATH)
    obs["datetime"] = pd.to_datetime(obs["datetime"])
    obs["depth_rounded_m"] = obs["depth"].round().astype(int)
    return obs.rename(columns={"temp": "temp_obs"})[
        ["datetime", "depth_rounded_m", "temp_obs"]
    ]


def rmse(values: pd.Series) -> float:
    return float(np.sqrt(np.mean(np.square(values))))


start, lake_depth = load_config()
sim = load_simulation(start, lake_depth)
obs = load_observations()
matched = obs.merge(sim, on=["datetime", "depth_rounded_m"], how="inner")
matched["error"] = matched["temp_sim"] - matched["temp_obs"]

surface = matched[matched["depth_rounded_m"] <= SURFACE_MAX_DEPTH]
deep = matched[matched["depth_rounded_m"] >= DEEP_MIN_DEPTH]

report = {
    "lake_depth_m": float(lake_depth),
    "surface_max_depth_m": float(SURFACE_MAX_DEPTH),
    "deep_min_depth_m": float(DEEP_MIN_DEPTH),
    "valid_match_count": int(len(matched)),
    "total_rmse_c": round(rmse(matched["error"]), 4),
    "surface_rmse_c": round(rmse(surface["error"]), 4),
    "deep_rmse_c": round(rmse(deep["error"]), 4),
    "mean_bias_c": round(float(matched["error"].mean()), 4),
}

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, sort_keys=True)
    f.write("\n")
PY
