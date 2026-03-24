#!/bin/bash
set -e

python3 -u <<'PYTHON'
import os
import re
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd
from netCDF4 import Dataset
from scipy.optimize import minimize

SIM_FOLDER = "/root"
NML_PATH = os.path.join(SIM_FOLDER, "glm3.nml")
OUTPUT_PATH = os.path.join(SIM_FOLDER, "output", "dimictic_profile.nc")
OBS_PATH = os.path.join(SIM_FOLDER, "deep_profile_obs.csv")
LAKE_DEPTH = 25
START_DATE = datetime(2010, 1, 1, 12, 0, 0)
TARGET_RMSE = 1.65

OBS_DF = None
BEST_RMSE = 999.0
BEST_PARAMS = None
ITERATION = 0


class EarlyStopException(Exception):
    pass


def modify_nml(nml_path, params):
    with open(nml_path, "r") as handle:
        content = handle.read()
    for param, value in params.items():
        pattern = rf"({param}\s*=\s*)[\d\.\-e]+"
        content = re.sub(pattern, rf"\g<1>{value}", content)
    with open(nml_path, "w") as handle:
        handle.write(content)


def run_glm():
    result = subprocess.run(["glm"], cwd=SIM_FOLDER, capture_output=True, text=True)
    return result.returncode == 0


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
        return 999.0
    return float(np.sqrt(np.mean((merged["temp_sim"] - merged["temp_obs"]) ** 2)))


def objective(x):
    global BEST_PARAMS, BEST_RMSE, ITERATION

    Kw, coef_mix_hyp, wind_factor, lw_factor, ch = x
    if not (0.10 <= Kw <= 0.60 and 0.20 <= coef_mix_hyp <= 0.90 and 0.70 <= wind_factor <= 1.40 and 0.70 <= lw_factor <= 1.30 and 0.0005 <= ch <= 0.0020):
        return 999.0

    ITERATION += 1
    params = {
        "Kw": round(Kw, 4),
        "coef_mix_hyp": round(coef_mix_hyp, 4),
        "wind_factor": round(wind_factor, 4),
        "lw_factor": round(lw_factor, 4),
        "ch": round(ch, 6),
    }
    modify_nml(NML_PATH, params)
    if not run_glm():
        return 999.0

    sim_df = read_glm_output(OUTPUT_PATH)
    rmse = calculate_rmse(sim_df, OBS_DF)
    print(
        f"[{ITERATION:03d}] Kw={params['Kw']:.4f}, mix_hyp={params['coef_mix_hyp']:.4f}, "
        f"wind={params['wind_factor']:.4f}, lw={params['lw_factor']:.4f}, ch={params['ch']:.6f} -> RMSE={rmse:.3f}"
    )

    if rmse < BEST_RMSE:
        BEST_RMSE = rmse
        BEST_PARAMS = params.copy()

    if rmse < TARGET_RMSE:
        raise EarlyStopException()

    return rmse


def main():
    global OBS_DF

    OBS_DF = read_observations(OBS_PATH)
    initial_points = [
        [0.30, 0.50, 1.00, 1.00, 0.0013],
        [0.34, 0.45, 1.08, 0.96, 0.0011],
    ]

    for guess in initial_points:
        try:
            minimize(
                objective,
                guess,
                method="Nelder-Mead",
                options={"maxiter": 80, "xatol": 0.01, "fatol": 0.02},
            )
        except EarlyStopException:
            break

    if BEST_PARAMS is None:
        raise RuntimeError("Calibration did not produce any valid parameter set.")

    modify_nml(NML_PATH, BEST_PARAMS)
    if not run_glm():
        raise RuntimeError("GLM failed when re-running the best parameter set.")

    print(f"Final RMSE: {BEST_RMSE:.3f} C")
    print(f"Best parameters: {BEST_PARAMS}")


if __name__ == "__main__":
    main()
PYTHON
