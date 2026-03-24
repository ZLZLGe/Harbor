import os
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd
from netCDF4 import Dataset

LAKE_DEPTH = 25
SIM_FOLDER = "/root"
OUTPUT_PATH = os.path.join(SIM_FOLDER, "output", "dimictic_profile.nc")
OBS_PATH = os.path.join(SIM_FOLDER, "deep_profile_obs.csv")
START_DATE = datetime(2010, 1, 1, 12, 0, 0)


def read_glm_output(nc_path):
    nc = Dataset(nc_path, "r")
    time = nc.variables["time"][:]
    z = nc.variables["z"][:]
    temp = nc.variables["temp"][:]
    records = []
    for t_idx in range(len(time)):
        hours = float(time[t_idx])
        timestamp = pd.Timestamp(START_DATE) + pd.Timedelta(hours=hours)
        heights = z[t_idx, :, 0, 0]
        temps = temp[t_idx, :, 0, 0]
        for d_idx in range(len(heights)):
            h_val = heights[d_idx]
            t_val = temps[d_idx]
            if not np.ma.is_masked(h_val) and not np.ma.is_masked(t_val):
                depth = LAKE_DEPTH - float(h_val)
                if 0 <= depth <= LAKE_DEPTH:
                    records.append(
                        {
                            "datetime": timestamp,
                            "depth": round(depth),
                            "temp_sim": float(t_val),
                        }
                    )
    nc.close()
    df = pd.DataFrame(records)
    return df.groupby(["datetime", "depth"]).agg({"temp_sim": "mean"}).reset_index()


def read_observations(obs_path):
    df = pd.read_csv(obs_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["depth"] = df["depth"].round().astype(int)
    return df.rename(columns={"temp": "temp_obs"})[["datetime", "depth", "temp_obs"]]


def calculate_rmse(sim_df, obs_df):
    merged = pd.merge(obs_df, sim_df, on=["datetime", "depth"], how="inner")
    if len(merged) == 0:
        return 999.0, 0
    rmse = float(np.sqrt(np.mean((merged["temp_sim"] - merged["temp_obs"]) ** 2)))
    return rmse, len(merged)


class TestDimicticCalibration:
    def test_glm_runs(self):
        result = subprocess.run(["glm"], cwd=SIM_FOLDER, capture_output=True, text=True)
        assert result.returncode == 0, f"GLM failed: {result.stderr}"

    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), "dimictic_profile.nc not found"

    def test_output_coverage(self):
        sim_df = read_glm_output(OUTPUT_PATH)
        assert sim_df["datetime"].min() <= pd.Timestamp("2010-01-02 12:00:00")
        assert sim_df["datetime"].max() >= pd.Timestamp("2015-12-29 12:00:00")

    def test_rmse_threshold(self):
        sim_df = read_glm_output(OUTPUT_PATH)
        obs_df = read_observations(OBS_PATH)
        rmse, matched = calculate_rmse(sim_df, obs_df)
        assert matched >= 2000, f"Only {matched} observation points matched the simulation output"
        assert rmse < 1.8, f"RMSE {rmse:.3f}C >= 1.8C threshold"
