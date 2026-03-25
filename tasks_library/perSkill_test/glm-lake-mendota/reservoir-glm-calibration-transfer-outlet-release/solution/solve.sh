#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TASK_ROOT=${TASK_ROOT:-/root}

if command -v glm >/dev/null 2>&1; then
  export GLM_BIN="glm"
else
  export GLM_BIN="${SCRIPT_DIR}/../environment/glm"
fi

python3 -u <<'PY'
import math
import os
import random
import re
import subprocess
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
GLM_BIN = os.environ["GLM_BIN"]
NML_PATH = TASK_ROOT / "glm3.nml"
OBS_PATH = TASK_ROOT / "inputs" / "release_temperature_observed.csv"
FORCING_PATH = TASK_ROOT / "inputs" / "reservoir_forcing.csv"
SCHEDULE_PATH = TASK_ROOT / "inputs" / "release_schedule.csv"
MODEL_OUTPUT_PATH = TASK_ROOT / "output" / "release_temperature_daily.csv"
REPORT_PATH = TASK_ROOT / "reports" / "release_temperature_fit.csv"
PARAM_ORDER = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]
BOUNDS = {
    "Kw": (0.12, 0.50),
    "coef_mix_hyp": (0.30, 1.10),
    "wind_factor": (0.70, 1.40),
    "lw_factor": (0.75, 1.15),
    "ch": (0.0008, 0.0024),
}


def write_params(params):
    text = NML_PATH.read_text()
    for key, value in params.items():
        text = re.sub(rf"({key}\s*=\s*)[-0-9.]+", rf"\g<1>{value:.6f}", text)
    NML_PATH.write_text(text)


def run_model():
    env = dict(os.environ)
    env["TASK_ROOT"] = str(TASK_ROOT)
    completed = subprocess.run([GLM_BIN], cwd=TASK_ROOT, env=env, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    return pd.read_csv(MODEL_OUTPUT_PATH)


def simulate_locally(forcing, schedule, params):
    frame = forcing.merge(schedule, on="date", how="inner").sort_values("date").reset_index(drop=True)
    surface_temp = 12.0
    deep_temp = 7.8
    total_days = len(frame)
    rows = []

    for idx, row in frame.iterrows():
        season = math.sin(2.0 * math.pi * (idx + 15) / total_days)
        surface_temp = (
            surface_temp
            + 0.10 * (row["air_temp_c"] - surface_temp)
            + 0.0018 * row["shortwave_wm2"] * params["lw_factor"]
            - 0.55 * params["Kw"]
            - 0.08 * row["wind_speed_mps"] * params["wind_factor"]
            + 0.05 * (row["inflow_temp_c"] - surface_temp)
            + 0.12 * season
        )
        exchange = 0.030 * params["coef_mix_hyp"] * (surface_temp - deep_temp) + 250.0 * params["ch"] * (row["release_cms"] / 30.0)
        attenuation = 0.008 * row["shortwave_wm2"] * math.exp(-params["Kw"] * max(row["withdrawal_depth_m"] - 6.0, 1.0) / 7.5)
        deep_temp = deep_temp + 0.025 * (row["inflow_temp_c"] - deep_temp) + attenuation + 0.55 * exchange - 0.035 * params["wind_factor"] + 0.03 * season
        outlet_fraction = min(
            0.62,
            max(
                0.05,
                0.10 + 0.18 * params["coef_mix_hyp"] - 0.07 * params["Kw"] - 0.012 * (row["withdrawal_depth_m"] - 12.0),
            ),
        )
        release_temp = outlet_fraction * surface_temp + (1.0 - outlet_fraction) * deep_temp + 0.015 * (row["release_cms"] - 24.0)
        rows.append({"date": row["date"], "simulated_release_temp_c": release_temp})

    return pd.DataFrame(rows)


def score(params, observations, forcing, schedule):
    simulated = simulate_locally(forcing, schedule, params)
    merged = observations.merge(simulated, on="date", how="inner")
    if merged.empty:
        return float("inf"), float("inf"), float("inf"), merged
    merged["error"] = merged["simulated_release_temp_c"] - merged["observed_release_temp_c"]
    rmse = float((merged["error"] ** 2).mean() ** 0.5)
    max_abs_error = float(merged["error"].abs().max())
    mean_bias = float(merged["error"].mean())
    return rmse, max_abs_error, mean_bias, merged


def random_search(observations, forcing, schedule):
    random.seed(0)
    best = {
        "Kw": 0.38,
        "coef_mix_hyp": 0.45,
        "wind_factor": 0.85,
        "lw_factor": 1.08,
        "ch": 0.00110,
    }
    best_rmse, _, _, _ = score(best, observations, forcing, schedule)
    widths = {key: BOUNDS[key][1] - BOUNDS[key][0] for key in PARAM_ORDER}

    for _stage in range(8):
        for _ in range(200):
            candidate = {}
            for key in PARAM_ORDER:
                low = max(BOUNDS[key][0], best[key] - widths[key] / 2.0)
                high = min(BOUNDS[key][1], best[key] + widths[key] / 2.0)
                candidate[key] = random.uniform(low, high)
            rmse, _, _, _ = score(candidate, observations, forcing, schedule)
            if rmse < best_rmse:
                best = candidate
                best_rmse = rmse
        for key in PARAM_ORDER:
            widths[key] *= 0.5

    return best


def main():
    observations = pd.read_csv(OBS_PATH)
    forcing = pd.read_csv(FORCING_PATH)
    schedule = pd.read_csv(SCHEDULE_PATH)
    best = random_search(observations, forcing, schedule)
    write_params(best)
    model_output = run_model()[["date", "simulated_release_temp_c"]]
    merged = observations.merge(model_output, on="date", how="inner")
    merged["error"] = merged["simulated_release_temp_c"] - merged["observed_release_temp_c"]
    rmse = float((merged["error"] ** 2).mean() ** 0.5)
    max_abs_error = float(merged["error"].abs().max())
    mean_bias = float(merged["error"].mean())
    merged["abs_error_c"] = merged["error"].abs()
    report = (
        merged.rename(columns={"observed_release_temp_c": "observed_release_temp_c"})
        [["date", "observed_release_temp_c", "simulated_release_temp_c", "abs_error_c"]]
        .sort_values("date")
        .reset_index(drop=True)
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORT_PATH, index=False, float_format="%.6f")
    print(f"RMSE={rmse:.6f}")
    print(f"max_abs_error={max_abs_error:.6f}")
    print(f"mean_bias={mean_bias:.6f}")


if __name__ == "__main__":
    main()
PY
