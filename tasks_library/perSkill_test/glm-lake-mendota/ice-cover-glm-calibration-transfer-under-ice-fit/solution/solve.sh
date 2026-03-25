#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TASK_ROOT=${TASK_ROOT:-/root}

if command -v glm >/dev/null 2>&1; then
  export GLM_BIN="glm"
else
  export GLM_BIN="${SCRIPT_DIR}/../environment/glm"
fi

python3 - <<'PY'
import itertools
import json
import math
import os
import re
import subprocess
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
GLM_BIN = os.environ["GLM_BIN"]
NML_PATH = TASK_ROOT / "glm3.nml"
FORCING_PATH = TASK_ROOT / "inputs" / "winter_forcing.csv"
OBS_PATH = TASK_ROOT / "inputs" / "observed_under_ice_profiles.csv"
TARGETS_PATH = TASK_ROOT / "inputs" / "ice_event_targets.json"
OUTPUT_PATH = TASK_ROOT / "output" / "under_ice_profiles.csv"
REPORT_PATH = TASK_ROOT / "analysis" / "under_ice_fit_summary.json"
DEPTHS = [0.0, 1.0, 2.0, 3.5, 5.0, 6.5, 8.0, 10.0, 12.0]
PARAM_KEYS = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]


def replace_param(text, key, value):
    return re.sub(rf"({key}\s*=\s*)[-0-9.]+", rf"\g<1>{value}", text)


def write_params(params):
    text = NML_PATH.read_text()
    for key, value in params.items():
        formatted = f"{value:.6f}" if key == "ch" else f"{value:.4f}"
        text = replace_param(text, key, formatted)
    NML_PATH.write_text(text)


def read_dates():
    text = NML_PATH.read_text()
    start = re.search(r"start\s*=\s*'([^']+)'", text).group(1)
    stop = re.search(r"stop\s*=\s*'([^']+)'", text).group(1)
    return start[:10], stop[:10]


def simulate_profiles(params, forcing):
    start_date = pd.Timestamp(read_dates()[0]).date()
    stop_date = pd.Timestamp(read_dates()[1]).date()
    total_days = max(1, (stop_date - start_date).days)
    records = []
    for forcing_row in forcing.itertuples(index=False):
        current_date = forcing_row.date.date()
        progress = (current_date - start_date).days / total_days
        freeze_core = max(0.0, -forcing_row.air_temp_c - 0.5)
        seasonal = max(0.0, math.sin(math.pi * progress))

        ice_signal = (
            0.55 * freeze_core
            + 0.08 * forcing_row.snow_cm
            + 0.95 * seasonal
            - 0.006 * forcing_row.shortwave_wm2
            - 0.24 * forcing_row.wind_speed_mps * params["wind_factor"]
            + 10.5 * (params["Kw"] - 0.24)
            - 6.5 * (params["coef_mix_hyp"] - 0.48)
            - 5200.0 * (params["ch"] - 0.0011)
            - 2.1 * (params["lw_factor"] - 0.95)
        )
        ice_thickness = max(0.0, min(0.85, 0.04 * ice_signal))

        surface_temp = (
            0.28
            - 0.55 * ice_thickness
            + 0.004 * forcing_row.shortwave_wm2
            - 0.015 * freeze_core
            + 0.9 * (params["lw_factor"] - 0.95)
            + 450.0 * (params["ch"] - 0.0011)
            - 0.16 * (params["Kw"] - 0.24)
        )
        surface_temp = max(-0.05, min(0.65, surface_temp))

        bottom_temp = (
            3.25
            + 0.18 * forcing_row.inflow_temp_c
            + 1.8 * (params["Kw"] - 0.24)
            + 1.3 * (params["lw_factor"] - 0.95)
            + 3.6 * (params["coef_mix_hyp"] - 0.48)
            - 1.05 * (params["wind_factor"] - 1.0)
            + 850.0 * (params["ch"] - 0.0011)
            - 0.12 * ice_thickness
        )

        inversion_center = (
            2.4
            + 5.8 * ice_thickness
            + 10.0 * (params["Kw"] - 0.24)
            - 7.2 * (params["coef_mix_hyp"] - 0.48)
            + 2.0 * (params["wind_factor"] - 1.0)
            - 4.0 * (params["lw_factor"] - 0.95)
            - 1600.0 * (params["ch"] - 0.0011)
        )
        inversion_center = max(1.2, min(11.0, inversion_center))

        sharpness = max(
            0.8,
            1.25
            + 2.2 * (params["Kw"] - 0.24)
            - 1.4 * (params["coef_mix_hyp"] - 0.48)
            + 0.35 * (params["wind_factor"] - 1.0),
        )

        for depth_m in DEPTHS:
            logistic = 0.5 * (1.0 + math.tanh((depth_m - inversion_center) / sharpness))
            temperature_c = surface_temp + (bottom_temp - surface_temp) * logistic
            temperature_c += 0.04 * math.cos(depth_m / 1.8 + progress * 4.5)
            records.append(
                {
                    "date": current_date.isoformat(),
                    "depth_m": round(depth_m, 1),
                    "temperature_c": round(float(temperature_c), 6),
                    "ice_thickness_m": round(float(ice_thickness), 6),
                }
            )
    return pd.DataFrame.from_records(records)


def two_degree_isotherm_depth(profile_df):
    profile_df = profile_df.sort_values("depth_m").reset_index(drop=True)
    pairs = list(zip(profile_df["depth_m"], profile_df["temperature_c"]))
    for (depth_1, temp_1), (depth_2, temp_2) in zip(pairs[:-1], pairs[1:]):
        if abs(temp_1 - 2.0) <= 1e-12:
            return round(float(depth_1), 6)
        if (temp_1 - 2.0) * (temp_2 - 2.0) <= 0 and temp_1 != temp_2:
            fraction = (2.0 - temp_1) / (temp_2 - temp_1)
            return round(float(depth_1 + fraction * (depth_2 - depth_1)), 6)
    raise ValueError("Could not locate 2.0C isotherm")


def derive_key_dates(simulation_df):
    daily_rows = []
    for sample_date, profile_df in simulation_df.groupby("date"):
        profile_df = profile_df.sort_values("depth_m").reset_index(drop=True)
        surface_temp = float(profile_df.iloc[0]["temperature_c"])
        bottom_temp = float(profile_df.iloc[-1]["temperature_c"])
        ice_thickness = float(profile_df.iloc[0]["ice_thickness_m"])
        two_degree_depth = two_degree_isotherm_depth(profile_df)
        daily_rows.append(
            {
                "date": sample_date,
                "surface_temp_c": surface_temp,
                "bottom_temp_c": bottom_temp,
                "ice_thickness_m": ice_thickness,
                "two_degree_isotherm_depth_m": two_degree_depth,
            }
        )
    daily_df = pd.DataFrame(daily_rows).sort_values("date").reset_index(drop=True)
    ice_rows = daily_df[daily_df["ice_thickness_m"] >= 0.05]
    stable_rows = daily_df[
        (daily_df["ice_thickness_m"] >= 0.05)
        & ((daily_df["bottom_temp_c"] - daily_df["surface_temp_c"]) >= 2.8)
        & (daily_df["two_degree_isotherm_depth_m"] >= 3.6)
    ]
    ice_onset = None if ice_rows.empty else str(ice_rows.iloc[0]["date"])
    stable_inverse = None if stable_rows.empty else str(stable_rows.iloc[0]["date"])
    peak_ice = daily_df.loc[daily_df["ice_thickness_m"].idxmax(), "date"]
    return {
        "simulated_ice_onset": ice_onset,
        "simulated_stable_inverse_onset": stable_inverse,
        "simulated_peak_ice_date": str(peak_ice),
    }


def compute_metrics(simulation_df, observations_df):
    sample_dates = sorted(observations_df["sample_date"].unique().tolist())
    sim_sample = simulation_df[simulation_df["date"].isin(sample_dates)].copy()
    merged = observations_df.merge(
        sim_sample,
        left_on=["sample_date", "depth_m"],
        right_on=["date", "depth_m"],
        how="inner",
        suffixes=("_obs", "_sim"),
    )
    merged["sq_error"] = (merged["temperature_c_obs"] - merged["temperature_c_sim"]) ** 2
    overall_rmse = math.sqrt(float(merged["sq_error"].mean()))

    bottom_bias = []
    comparison = []
    for sample_date in sample_dates:
        obs_profile = observations_df[observations_df["sample_date"] == sample_date].copy()
        sim_profile = sim_sample[sim_sample["date"] == sample_date].copy()
        observed_depth = two_degree_isotherm_depth(obs_profile.rename(columns={"sample_date": "date"}))
        simulated_depth = two_degree_isotherm_depth(sim_profile)
        observed_bottom = float(obs_profile.sort_values("depth_m").iloc[-1]["temperature_c"])
        simulated_bottom = float(sim_profile.sort_values("depth_m").iloc[-1]["temperature_c"])
        bottom_bias.append(abs(simulated_bottom - observed_bottom))
        comparison.append(
            {
                "sample_date": sample_date,
                "observed_depth_m": observed_depth,
                "simulated_depth_m": simulated_depth,
                "abs_error_m": round(abs(simulated_depth - observed_depth), 6),
                "observed_bottom_temp_c": round(observed_bottom, 6),
                "simulated_bottom_temp_c": round(simulated_bottom, 6),
            }
        )

    mean_iso_bias = sum(item["abs_error_m"] for item in comparison) / len(comparison)
    max_iso_bias = max(item["abs_error_m"] for item in comparison)
    max_bottom_bias = max(bottom_bias)
    return {
        "overall_profile_rmse_c": round(overall_rmse, 6),
        "max_bottom_bias_c": round(max_bottom_bias, 6),
        "mean_abs_two_degree_isotherm_bias_m": round(mean_iso_bias, 6),
        "max_abs_two_degree_isotherm_bias_m": round(max_iso_bias, 6),
        "comparison": comparison,
        "sampled_profile_dates": len(sample_dates),
    }


def objective_tuple(params, forcing, observations, targets):
    simulation_df = simulate_profiles(params, forcing)
    metrics = compute_metrics(simulation_df, observations)
    key_dates = derive_key_dates(simulation_df)
    mismatch_penalty = sum(
        [
            key_dates["simulated_ice_onset"] != targets["ice_onset_date"],
            key_dates["simulated_stable_inverse_onset"] != targets["stable_inverse_onset_date"],
            key_dates["simulated_peak_ice_date"] != targets["peak_ice_date"],
        ]
    )
    return (
        mismatch_penalty,
        metrics["overall_profile_rmse_c"],
        metrics["max_bottom_bias_c"],
        metrics["mean_abs_two_degree_isotherm_bias_m"],
        metrics["max_abs_two_degree_isotherm_bias_m"],
        params,
        metrics,
        key_dates,
    )


def main():
    forcing = pd.read_csv(FORCING_PATH, parse_dates=["date"])
    observations = pd.read_csv(OBS_PATH)
    observations["sample_date"] = observations["sample_date"].astype(str)
    targets = json.loads(TARGETS_PATH.read_text())

    candidate_space = {
        "Kw": [0.24, 0.26, 0.28, 0.30, 0.32],
        "coef_mix_hyp": [0.40, 0.44, 0.48, 0.52],
        "wind_factor": [0.89, 0.93, 0.97, 1.01],
        "lw_factor": [0.93, 0.95, 0.97, 0.99],
        "ch": [0.00110, 0.00114, 0.00118, 0.00122],
    }

    best = None
    for values in itertools.product(*(candidate_space[key] for key in PARAM_KEYS)):
        params = {
            "Kw": round(values[0], 4),
            "coef_mix_hyp": round(values[1], 4),
            "wind_factor": round(values[2], 4),
            "lw_factor": round(values[3], 4),
            "ch": round(values[4], 6),
        }
        candidate = objective_tuple(params, forcing, observations, targets)
        if best is None or candidate[:5] < best[:5]:
            best = candidate

    if best is None:
        raise RuntimeError("No feasible parameter set found")

    _, _, _, _, _, params, metrics, key_dates = best
    write_params(params)

    completed = subprocess.run(
        [GLM_BIN],
        cwd=TASK_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "TASK_ROOT": str(TASK_ROOT)},
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)

    rerun_df = pd.read_csv(OUTPUT_PATH)
    rerun_metrics = compute_metrics(rerun_df, observations)
    rerun_key_dates = derive_key_dates(rerun_df)

    report = {
        "lake": "North Star Bay",
        "simulation_window": {
            "start": "2021-12-01",
            "end": "2022-03-15",
        },
        "sampled_profile_dates": rerun_metrics["sampled_profile_dates"],
        "key_dates": {
            "observed_ice_onset": targets["ice_onset_date"],
            "simulated_ice_onset": rerun_key_dates["simulated_ice_onset"],
            "observed_stable_inverse_onset": targets["stable_inverse_onset_date"],
            "simulated_stable_inverse_onset": rerun_key_dates["simulated_stable_inverse_onset"],
            "observed_peak_ice_date": targets["peak_ice_date"],
            "simulated_peak_ice_date": rerun_key_dates["simulated_peak_ice_date"],
        },
        "fit_metrics": {
            "overall_profile_rmse_c": rerun_metrics["overall_profile_rmse_c"],
            "max_bottom_bias_c": rerun_metrics["max_bottom_bias_c"],
            "mean_abs_two_degree_isotherm_bias_m": rerun_metrics["mean_abs_two_degree_isotherm_bias_m"],
            "max_abs_two_degree_isotherm_bias_m": rerun_metrics["max_abs_two_degree_isotherm_bias_m"],
        },
        "two_degree_isotherm_comparison": rerun_metrics["comparison"],
        "calibrated_parameters": params,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
PY
