#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import itertools
import json
import math
import os
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
NML_PATH = ROOT / "glm3.nml"
OBS_PATH = ROOT / "inputs" / "monona_sparse_profiles.csv"
FORCING_PATH = ROOT / "inputs" / "monona_forcing.csv"
RESULT_PATH = ROOT / "results" / "monona_profile_calibration.json"
OUTPUT_PATH = ROOT / "output" / "monona_profiles.csv"

PARAM_NAMES = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]


def replace_param(text, key, value):
    pattern = rf"({key}\s*=\s*)([-0-9.]+)"
    return re.sub(pattern, rf"\g<1>{value}", text)


def write_params(params):
    text = NML_PATH.read_text()
    for key, value in params.items():
        text = replace_param(text, key, value)
    NML_PATH.write_text(text)


def simulate_profiles(params, forcing, depths=None):
    rows = []
    if depths is None:
        depths = range(23)
    for _, forcing_row in forcing.iterrows():
        day_of_year = int(forcing_row["day_of_year"])
        season = math.sin(2.0 * math.pi * (day_of_year - 172) / 365.25)
        stratification = max(0.0, math.sin(2.0 * math.pi * (day_of_year - 110) / 365.25))
        cooling = max(0.0, -season)

        surface_temp = (
            6.2
            + 0.62 * forcing_row["air_temp_c"]
            + 0.0105 * forcing_row["shortwave_w_m2"]
            + 0.003 * (forcing_row["longwave_w_m2"] - 300.0)
            + 7.5 * (params["lw_factor"] - 1.0)
            + 3400.0 * (params["ch"] - 0.0013)
            - 1.7 * (params["wind_factor"] - 1.0)
            + 0.45 * season
        )
        deep_temp = (
            4.7
            + 0.16 * forcing_row["air_temp_c"]
            + 0.0012 * forcing_row["shortwave_w_m2"]
            + 2.6 * (params["lw_factor"] - 1.0)
            + 1150.0 * (params["ch"] - 0.0013)
            + 2.2 * (params["coef_mix_hyp"] - 0.5)
            - 1.4 * (params["Kw"] - 0.3)
            - 0.25 * cooling
        )
        decay_scale = (
            3.1
            - 2.0 * stratification
            + 5.1 * (params["Kw"] - 0.3)
            - 2.7 * (params["coef_mix_hyp"] - 0.5)
            + 1.35 * (params["wind_factor"] - 1.0)
            + 0.7 * (params["lw_factor"] - 1.0)
        )
        decay_scale = max(0.9, min(9.5, decay_scale))
        bend = (
            0.055
            + 0.025 * stratification
            + 0.03 * (params["coef_mix_hyp"] - 0.5)
            - 0.018 * (params["wind_factor"] - 1.0)
        )

        for depth_value in depths:
            depth = float(depth_value)
            temperature_c = deep_temp + (surface_temp - deep_temp) * math.exp(-depth / decay_scale)
            temperature_c -= bend * depth * stratification
            temperature_c += 0.06 * math.cos(depth / 3.7 + day_of_year / 44.0)
            rows.append(
                {
                    "sample_date": forcing_row["date"].strftime("%Y-%m-%d"),
                    "depth_m": depth,
                    "temperature_c": temperature_c,
                }
            )
    return pd.DataFrame(rows)


def compute_metrics(params, forcing, observations):
    selected_dates = set(observations["sample_date"])
    selected_depths = sorted(observations["depth_m"].unique())
    forcing_subset = forcing[forcing["date"].dt.strftime("%Y-%m-%d").isin(selected_dates)].copy()
    simulation = simulate_profiles(params, forcing_subset, depths=selected_depths)
    merged = observations.merge(simulation, on=["sample_date", "depth_m"], suffixes=("_obs", "_sim"))
    merged["sq_error"] = (merged["temperature_c_obs"] - merged["temperature_c_sim"]) ** 2
    overall_rmse = math.sqrt(merged["sq_error"].mean())
    per_profile = (
        merged.groupby("sample_date")["sq_error"]
        .mean()
        .map(math.sqrt)
        .reset_index(name="rmse_c")
    )
    return overall_rmse, float(per_profile["rmse_c"].max()), per_profile


def search_best_parameters(forcing, observations):
    best_metrics = None
    grid = {
        "Kw": [0.26, 0.30, 0.34, 0.38, 0.42],
        "coef_mix_hyp": [0.38, 0.42, 0.46, 0.50, 0.54],
        "wind_factor": [0.98, 1.025, 1.07, 1.115, 1.16],
        "lw_factor": [0.90, 0.93, 0.96, 0.99, 1.02],
        "ch": [0.00134, 0.00142, 0.00150, 0.00158, 0.00166],
    }

    for values in itertools.product(*(grid[name] for name in PARAM_NAMES)):
        params = {
            "Kw": round(values[0], 4),
            "coef_mix_hyp": round(values[1], 4),
            "wind_factor": round(values[2], 4),
            "lw_factor": round(values[3], 4),
            "ch": round(values[4], 6),
        }
        overall_rmse, max_profile_rmse, per_profile = compute_metrics(params, forcing, observations)
        candidate = (overall_rmse, max_profile_rmse, params, per_profile)
        if best_metrics is None or candidate[:2] < best_metrics[:2]:
            best_metrics = candidate
    return best_metrics


def main():
    ROOT.joinpath("results").mkdir(parents=True, exist_ok=True)
    ROOT.joinpath("output").mkdir(parents=True, exist_ok=True)

    forcing = pd.read_csv(FORCING_PATH, parse_dates=["date"])
    observations = pd.read_csv(OBS_PATH)

    overall_rmse, max_profile_rmse, params, per_profile = search_best_parameters(forcing, observations)
    write_params(params)
    subprocess.run(["glm"], cwd=ROOT, check=True)

    result = {
        "lake": "Monona",
        "simulation_window": {
            "start": "2012-01-01",
            "end": "2013-12-31",
        },
        "overall_rmse_c": round(overall_rmse, 6),
        "max_profile_rmse_c": round(max_profile_rmse, 6),
        "profile_count": int(per_profile.shape[0]),
        "calibrated_parameters": params,
        "profile_rmse_c": [
            {
                "sample_date": row.sample_date,
                "rmse_c": round(float(row.rmse_c), 6),
            }
            for row in per_profile.sort_values("sample_date").itertuples(index=False)
        ],
    }

    RESULT_PATH.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"Output written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
PY
