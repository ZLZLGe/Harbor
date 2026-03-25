#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"

python3 - <<'PY'
import json
import math
import os
import re
import subprocess
from datetime import datetime
from itertools import product
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
NML_PATH = TASK_ROOT / "glm3.nml"
FORCING_PATH = TASK_ROOT / "inputs" / "seasonal_forcing.csv"
OBS_PATH = TASK_ROOT / "inputs" / "observed_stratification_profiles.csv"
OUTPUT_PATH = TASK_ROOT / "output" / "seasonal_profiles.csv"
REPORT_PATH = TASK_ROOT / "diagnostics" / "stratification_phenology_report.json"
PARAM_KEYS = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]
DATE_FMT = "%Y-%m-%d"


def read_nml_text():
    return NML_PATH.read_text()


def set_params(params):
    text = read_nml_text()
    for key, value in params.items():
        text = re.sub(rf"({key}\s*=\s*)[-0-9.]+", rf"\g<1>{value:.6f}", text)
    NML_PATH.write_text(text)


def read_nml_params():
    text = read_nml_text()
    params = {}
    for key in PARAM_KEYS:
        match = re.search(rf"{key}\s*=\s*([-0-9.]+)", text)
        if not match:
            raise ValueError(f"Missing parameter {key}")
        params[key] = float(match.group(1))
    return params


def derive_profile_metrics(profile_df):
    profile_df = profile_df.sort_values("depth_m").reset_index(drop=True)
    gradients = []
    for upper, lower in zip(profile_df.iloc[:-1].itertuples(index=False), profile_df.iloc[1:].itertuples(index=False)):
        gradient = (upper.temperature_c - lower.temperature_c) / (lower.depth_m - upper.depth_m)
        gradients.append((gradient, round((upper.depth_m + lower.depth_m) / 2.0, 3)))
    max_gradient, thermocline_depth = max(gradients, key=lambda item: item[0])
    surface_bottom_delta = float(profile_df.iloc[0]["temperature_c"] - profile_df.iloc[-1]["temperature_c"])
    is_stratified = surface_bottom_delta >= 1.5 and max_gradient >= 0.3
    return {
        "surface_bottom_delta_c": round(surface_bottom_delta, 6),
        "max_gradient_c_per_m": round(float(max_gradient), 6),
        "thermocline_depth_m": round(float(thermocline_depth), 3) if is_stratified else None,
        "is_stratified": is_stratified,
    }


def collect_profile_metrics(frame, date_column):
    metrics = {}
    for profile_date, profile_df in frame.groupby(date_column):
        metrics[str(profile_date)] = derive_profile_metrics(profile_df)
    return metrics


def get_events(profile_dates, metrics):
    onset = next(profile_date for profile_date in profile_dates if metrics[profile_date]["is_stratified"])
    onset_dt = datetime.strptime(onset, DATE_FMT).date()
    breakdown = None
    for profile_date in profile_dates:
        current_dt = datetime.strptime(profile_date, DATE_FMT).date()
        if current_dt >= datetime(2015, 9, 1).date() and current_dt > onset_dt and not metrics[profile_date]["is_stratified"]:
            breakdown = profile_date
            break
    if breakdown is None:
        raise ValueError("Could not determine breakdown date")
    return onset, breakdown


def simulate_profiles(forcing_df, params, start, stop):
    total_days = max(1, (stop - start).days)
    rows = []
    for forcing_row in forcing_df.itertuples(index=False):
        current_date = forcing_row.date.date()
        if current_date < start or current_date > stop:
            continue
        progress = (current_date - start).days / total_days
        heating = max(0.0, math.sin(math.pi * (progress - 0.03)))
        cooling = max(0.0, math.sin(math.pi * max(progress - 0.58, 0.0) / (1.0 - 0.58)))

        strat_strength = (
            0.6
            + 7.2 * heating
            + 0.016 * (forcing_row.shortwave_wm2 - 180.0)
            + 0.22 * (forcing_row.air_temp_c - 10.0)
            + 28.0 * (params["lw_factor"] - 1.0)
            + 6000.0 * (params["ch"] - 0.0013)
            - 1.35 * forcing_row.wind_speed_mps * params["wind_factor"]
            - 5.0 * (params["coef_mix_hyp"] - 0.5)
            - 4.6 * cooling
        )
        strat_strength = max(0.0, strat_strength)

        thermocline_depth = (
            1.2
            + 7.6 * heating
            - 5.2 * cooling
            + 22.0 * (params["Kw"] - 0.2)
            - 7.5 * (params["coef_mix_hyp"] - 0.5)
            + 1.8 * (params["wind_factor"] - 1.0)
            + 0.6 * (forcing_row.cloud_fraction - 0.4)
        )
        thermocline_depth = min(13.5, max(1.0, thermocline_depth))

        bottom_temp = (
            4.4
            + 0.05 * (forcing_row.air_temp_c - 10.0)
            + 420.0 * (params["ch"] - 0.0013)
            + 1.4 * (params["coef_mix_hyp"] - 0.5)
            - 0.6 * cooling
        )
        sharpness = max(
            0.55,
            1.2
            + 3.0 * (params["Kw"] - 0.2)
            - 1.6 * (params["coef_mix_hyp"] - 0.5)
            + 0.25 * (params["wind_factor"] - 1.0),
        )

        for depth_m in [0.0, 0.8, 1.9, 3.1, 4.6, 6.2, 7.9, 9.7, 11.6, 13.6, 15.7, 17.9]:
            temperature_c = bottom_temp + 0.5 * strat_strength * (1.0 - math.tanh((depth_m - thermocline_depth) / sharpness))
            temperature_c += 0.05 * math.cos(depth_m / 2.3 + progress * 5.0)
            rows.append(
                {
                    "date": current_date.isoformat(),
                    "depth_m": round(depth_m, 1),
                    "temperature_c": round(float(temperature_c), 6),
                }
            )
    return pd.DataFrame.from_records(rows)


def evaluate(sim_df, obs_df):
    obs_metrics = collect_profile_metrics(obs_df, "sample_date")
    sample_dates = sorted(obs_metrics.keys())
    sim_sample = sim_df[sim_df["date"].isin(sample_dates)].copy()
    sim_metrics = collect_profile_metrics(sim_sample, "date")

    observed_onset, observed_breakdown = get_events(sample_dates, obs_metrics)
    simulated_onset, simulated_breakdown = get_events(sample_dates, sim_metrics)

    comparison = []
    for sample_date in sample_dates:
        obs_item = obs_metrics[sample_date]
        sim_item = sim_metrics[sample_date]
        if obs_item["is_stratified"] and sim_item["is_stratified"]:
            comparison.append(
                {
                    "sample_date": sample_date,
                    "observed_depth_m": round(obs_item["thermocline_depth_m"], 3),
                    "simulated_depth_m": round(sim_item["thermocline_depth_m"], 3),
                    "abs_error_m": round(abs(obs_item["thermocline_depth_m"] - sim_item["thermocline_depth_m"]), 6),
                    "observed_surface_bottom_delta_c": round(obs_item["surface_bottom_delta_c"], 6),
                    "simulated_surface_bottom_delta_c": round(sim_item["surface_bottom_delta_c"], 6),
                }
            )

    if not comparison:
        return None

    mean_abs_error = sum(item["abs_error_m"] for item in comparison) / len(comparison)
    max_abs_error = max(item["abs_error_m"] for item in comparison)
    surface_bottom_rmse = math.sqrt(
        sum(
            (obs_metrics[sample_date]["surface_bottom_delta_c"] - sim_metrics[sample_date]["surface_bottom_delta_c"]) ** 2
            for sample_date in sample_dates
        )
        / len(sample_dates)
    )

    score = (
        mean_abs_error
        + 0.8 * max_abs_error
        + 0.6 * surface_bottom_rmse
        + 0.05 * abs((datetime.strptime(simulated_onset, DATE_FMT) - datetime.strptime(observed_onset, DATE_FMT)).days)
        + 0.05 * abs((datetime.strptime(simulated_breakdown, DATE_FMT) - datetime.strptime(observed_breakdown, DATE_FMT)).days)
        + 2.0 * abs(len(comparison) - sum(1 for value in obs_metrics.values() if value["is_stratified"]))
    )

    return {
        "score": score,
        "sample_dates": sample_dates,
        "obs_metrics": obs_metrics,
        "sim_metrics": sim_metrics,
        "comparison": comparison,
        "event_dates": {
            "observed_onset": observed_onset,
            "simulated_onset": simulated_onset,
            "observed_breakdown": observed_breakdown,
            "simulated_breakdown": simulated_breakdown,
            "onset_error_days": abs((datetime.strptime(simulated_onset, DATE_FMT) - datetime.strptime(observed_onset, DATE_FMT)).days),
            "breakdown_error_days": abs((datetime.strptime(simulated_breakdown, DATE_FMT) - datetime.strptime(observed_breakdown, DATE_FMT)).days),
        },
        "thermocline_depth_metrics": {
            "matched_profile_count": len(comparison),
            "mean_abs_error_m": round(mean_abs_error, 6),
            "max_abs_error_m": round(max_abs_error, 6),
        },
        "surface_bottom_delta_rmse_c": round(surface_bottom_rmse, 6),
    }


def main():
    forcing_df = pd.read_csv(FORCING_PATH, parse_dates=["date"])
    obs_df = pd.read_csv(OBS_PATH)
    obs_df["sample_date"] = obs_df["sample_date"].astype(str)

    text = read_nml_text()
    start = datetime.strptime(re.search(r"start\s*=\s*'([^']+)'", text).group(1), "%Y-%m-%d %H:%M:%S").date()
    stop = datetime.strptime(re.search(r"stop\s*=\s*'([^']+)'", text).group(1), "%Y-%m-%d %H:%M:%S").date()

    candidate_space = {
        "Kw": [0.20, 0.22, 0.24, 0.26, 0.28],
        "coef_mix_hyp": [0.50, 0.54, 0.58, 0.62],
        "wind_factor": [0.96, 1.00, 1.04, 1.08],
        "lw_factor": [1.00, 1.04, 1.08, 1.12],
        "ch": [0.00136, 0.00142, 0.00148, 0.00154],
    }

    best = None
    for values in product(*candidate_space.values()):
        params = dict(zip(candidate_space.keys(), values))
        sim_df = simulate_profiles(forcing_df, params, start, stop)
        metrics = evaluate(sim_df, obs_df)
        if metrics is None:
            continue
        if best is None or metrics["score"] < best["score"]:
            best = {"params": params, **metrics}

    if best is None:
        raise RuntimeError("No feasible parameter set found")

    set_params(best["params"])
    completed = subprocess.run(
        ["glm"],
        cwd=TASK_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "TASK_ROOT": str(TASK_ROOT)},
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)

    final_output = pd.read_csv(OUTPUT_PATH)
    final_metrics = evaluate(final_output, obs_df)
    final_params = read_nml_params()

    report = {
        "lake": "Pine Ridge Lake",
        "season": {"start": "2015-04-01", "end": "2015-10-31"},
        "sampled_profile_dates": len(final_metrics["sample_dates"]),
        "event_dates": final_metrics["event_dates"],
        "thermocline_depth_metrics": final_metrics["thermocline_depth_metrics"],
        "surface_bottom_delta_rmse_c": final_metrics["surface_bottom_delta_rmse_c"],
        "thermocline_depth_comparison": final_metrics["comparison"],
        "calibrated_parameters": {key: round(final_params[key], 6) for key in PARAM_KEYS},
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
PY
