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
OBS_PATH = os.path.join(SIM_FOLDER, "reservoir_profile_obs.csv")
NML_PATH = os.path.join(SIM_FOLDER, "glm3.nml")
OUTPUT_PATH = os.path.join(SIM_FOLDER, "output", "temperate_profile.nc")
LAKE_DEPTH = 25
TARGET_RMSE = 1.75
BEST_RMSE = float("inf")
BEST_PARAMS = None
BEST_VECTOR = None
RUN_COUNT = 0
OBS_DF = None

LIMITS = {
    "Kw": (0.1, 1.2),
    "coef_mix_hyp": (0.1, 1.5),
    "wind_factor": (0.6, 1.4),
    "lw_factor": (0.8, 1.2),
    "ch": (0.0008, 0.0030),
}
PARAM_ORDER = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]


class EarlyStopException(Exception):
    pass


def clip_vector(values):
    clipped = []
    for value, name in zip(values, PARAM_ORDER):
        low, high = LIMITS[name]
        clipped.append(float(np.clip(value, low, high)))
    return clipped


def vector_to_params(values):
    values = clip_vector(values)
    return {
        "Kw": round(values[0], 4),
        "coef_mix_hyp": round(values[1], 4),
        "wind_factor": round(values[2], 4),
        "lw_factor": round(values[3], 4),
        "ch": round(values[4], 6),
    }


def modify_nml(nml_path, params):
    with open(nml_path, "r", encoding="utf-8") as handle:
        content = handle.read()
    for param, value in params.items():
        pattern = rf"({param}\s*=\s*)[\d\.\-eE]+"
        content = re.sub(pattern, rf"\g<1>{value}", content)
    with open(nml_path, "w", encoding="utf-8") as handle:
        handle.write(content)


def run_glm():
    result = subprocess.run(["glm"], cwd=SIM_FOLDER, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result.returncode == 0


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


def calculate_rmse(sim_df, obs_df):
    merged = pd.merge(obs_df, sim_df, on=["profile_time", "depth_m"], how="inner")
    if merged.empty:
        return 999.0
    return float(np.sqrt(np.mean((merged["water_temp_sim"] - merged["water_temp_c"]) ** 2)))


def evaluate(values, label):
    global BEST_RMSE, BEST_PARAMS, BEST_VECTOR, RUN_COUNT
    RUN_COUNT += 1
    params = vector_to_params(values)
    modify_nml(NML_PATH, params)
    if not run_glm():
        return 999.0
    sim_df = read_glm_output(OUTPUT_PATH)
    rmse = calculate_rmse(sim_df, OBS_DF)
    print(f"[{RUN_COUNT:02d}] {label} -> RMSE={rmse:.3f} with {params}")
    if rmse < BEST_RMSE:
        BEST_RMSE = rmse
        BEST_PARAMS = params.copy()
        BEST_VECTOR = [params[name] for name in PARAM_ORDER]
    if rmse < TARGET_RMSE:
        raise EarlyStopException()
    return rmse


def objective(values):
    return evaluate(values, "opt")


def main():
    global OBS_DF
    OBS_DF = read_observations(OBS_PATH)
    candidate_vectors = [
        [0.82, 0.95, 0.72, 1.08, 0.0018],
        [0.30, 0.50, 1.00, 1.00, 0.0013],
        [0.24, 0.42, 0.90, 0.97, 0.0011],
        [0.38, 0.62, 1.08, 1.02, 0.0015],
        [0.18, 0.33, 0.84, 0.94, 0.0010],
    ]

    try:
        for idx, candidate in enumerate(candidate_vectors, start=1):
            evaluate(candidate, f"seed-{idx}")

        minimize(
            objective,
            BEST_VECTOR or candidate_vectors[1],
            method="Nelder-Mead",
            options={"maxiter": 80, "xatol": 0.02, "fatol": 0.02},
        )
    except EarlyStopException:
        pass

    if BEST_PARAMS is None:
        raise RuntimeError("Calibration did not produce a valid GLM run.")

    modify_nml(NML_PATH, BEST_PARAMS)
    if not run_glm():
        raise RuntimeError("Final GLM run failed with best parameters.")

    if not os.path.exists(OUTPUT_PATH):
        raise FileNotFoundError(OUTPUT_PATH)

    print(f"Final RMSE: {BEST_RMSE:.3f}")
    print(f"Final parameters: {BEST_PARAMS}")


if __name__ == "__main__":
    main()
PYTHON
