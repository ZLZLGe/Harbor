import os
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd
from netCDF4 import Dataset

SIM_FOLDER = "/root"
OUTPUT_PATH = os.path.join(SIM_FOLDER, "output", "temperate_profile.nc")
OBS_PATH = os.path.join(SIM_FOLDER, "reservoir_profile_obs.csv")
LAKE_DEPTH = 25


def read_glm_output(nc_path):
    nc = Dataset(nc_path, "r")
    time = nc.variables["time"][:]
    z = nc.variables["z"][:]
    temp = nc.variables["temp"][:]
    start_date = datetime(2009, 1, 1, 12, 0, 0)
    records = []
    for t_idx in range(len(time)):
        profile_time = pd.Timestamp(start_date) + pd.Timedelta(hours=float(time[t_idx]))
        heights = z[t_idx, :, 0, 0]
        temps = temp[t_idx, :, 0, 0]
        for h_val, t_val in zip(heights, temps):
            if np.ma.is_masked(h_val) or np.ma.is_masked(t_val):
                continue
            depth = LAKE_DEPTH - float(h_val)
            if 0 <= depth <= LAKE_DEPTH:
                records.append(
                    {
                        "profile_time": profile_time,
                        "depth_m": round(depth),
                        "water_temp_sim": float(t_val),
                    }
                )
    nc.close()
    return (
        pd.DataFrame(records)
        .groupby(["profile_time", "depth_m"], as_index=False)
        .agg({"water_temp_sim": "mean"})
    )


def read_observations(obs_path):
    obs_df = pd.read_csv(obs_path)
    obs_df["profile_time"] = pd.to_datetime(obs_df["profile_time"])
    obs_df["depth_m"] = obs_df["depth_m"].round().astype(int)
    return obs_df[["profile_time", "depth_m", "water_temp_c"]]


def merge_profiles():
    sim_df = read_glm_output(OUTPUT_PATH)
    obs_df = read_observations(OBS_PATH)
    merged = pd.merge(obs_df, sim_df, on=["profile_time", "depth_m"], how="inner")
    return sim_df, obs_df, merged


def test_glm_runs_with_saved_parameters():
    result = subprocess.run(["glm"], cwd=SIM_FOLDER, capture_output=True, text=True)
    assert result.returncode == 0, f"GLM failed: {result.stderr}"


def test_primary_output_exists():
    assert os.path.exists(OUTPUT_PATH), f"{OUTPUT_PATH} not found"
    assert os.path.getsize(OUTPUT_PATH) > 0, f"{OUTPUT_PATH} is empty"


def test_growing_season_profile_rmse():
    _, _, merged = merge_profiles()
    assert len(merged) >= 2000, f"Too few matched profile points: {len(merged)}"
    rmse = float(np.sqrt(np.mean((merged["water_temp_sim"] - merged["water_temp_c"]) ** 2)))
    assert rmse < 1.8, f"Growing-season RMSE {rmse:.3f}C >= 1.8C"


def test_output_covers_observation_window():
    sim_df, obs_df, _ = merge_profiles()
    assert sim_df["profile_time"].min() <= obs_df["profile_time"].min()
    assert sim_df["profile_time"].max() >= obs_df["profile_time"].max()
