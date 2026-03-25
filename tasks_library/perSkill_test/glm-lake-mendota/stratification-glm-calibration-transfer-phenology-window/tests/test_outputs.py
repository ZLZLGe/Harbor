import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_PATH = TASK_ROOT / "output" / "seasonal_profiles.csv"
OBS_PATH = TASK_ROOT / "inputs" / "observed_stratification_profiles.csv"
NML_PATH = TASK_ROOT / "glm3.nml"
REPORT_PATH = TASK_ROOT / "diagnostics" / "stratification_phenology_report.json"
PARAM_KEYS = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]


def read_nml_params():
    text = NML_PATH.read_text()
    params = {}
    for key in PARAM_KEYS:
        match = re.search(rf"{key}\s*=\s*([-0-9.]+)", text)
        assert match, f"glm3.nml missing parameter {key}"
        params[key] = round(float(match.group(1)), 6)
    return params


def run_model():
    completed = subprocess.run(
        ["glm"],
        cwd=TASK_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "TASK_ROOT": str(TASK_ROOT)},
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert OUTPUT_PATH.exists(), "seasonal_profiles.csv was not generated"


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
    onset_dt = datetime.strptime(onset, "%Y-%m-%d").date()
    breakdown = None
    for profile_date in profile_dates:
        current_dt = datetime.strptime(profile_date, "%Y-%m-%d").date()
        if current_dt >= datetime(2015, 9, 1).date() and current_dt > onset_dt and not metrics[profile_date]["is_stratified"]:
            breakdown = profile_date
            break
    assert breakdown is not None, "Could not determine stratification breakdown date"
    return onset, breakdown


def compute_expected_metrics():
    observations = pd.read_csv(OBS_PATH)
    observations["sample_date"] = observations["sample_date"].astype(str)
    simulation = pd.read_csv(OUTPUT_PATH)
    simulation["date"] = simulation["date"].astype(str)

    obs_metrics = collect_profile_metrics(observations, "sample_date")
    sample_dates = sorted(obs_metrics.keys())
    sim_metrics = collect_profile_metrics(simulation[simulation["date"].isin(sample_dates)], "date")

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

    mean_abs_error = round(sum(item["abs_error_m"] for item in comparison) / len(comparison), 6)
    max_abs_error = round(max(item["abs_error_m"] for item in comparison), 6)
    surface_bottom_delta_rmse = round(
        (
            sum(
                (obs_metrics[sample_date]["surface_bottom_delta_c"] - sim_metrics[sample_date]["surface_bottom_delta_c"]) ** 2
                for sample_date in sample_dates
            )
            / len(sample_dates)
        )
        ** 0.5,
        6,
    )

    return {
        "sample_dates": sample_dates,
        "event_dates": {
            "observed_onset": observed_onset,
            "simulated_onset": simulated_onset,
            "observed_breakdown": observed_breakdown,
            "simulated_breakdown": simulated_breakdown,
            "onset_error_days": abs((datetime.strptime(simulated_onset, "%Y-%m-%d") - datetime.strptime(observed_onset, "%Y-%m-%d")).days),
            "breakdown_error_days": abs((datetime.strptime(simulated_breakdown, "%Y-%m-%d") - datetime.strptime(observed_breakdown, "%Y-%m-%d")).days),
        },
        "thermocline_depth_metrics": {
            "matched_profile_count": len(comparison),
            "mean_abs_error_m": mean_abs_error,
            "max_abs_error_m": max_abs_error,
        },
        "surface_bottom_delta_rmse_c": surface_bottom_delta_rmse,
        "comparison": comparison,
    }


def test_report_contract_and_thresholds():
    assert REPORT_PATH.exists(), "stratification_phenology_report.json not found"
    with REPORT_PATH.open() as handle:
        report = json.load(handle)

    assert report.get("lake") == "Pine Ridge Lake"
    assert report.get("season") == {"start": "2015-04-01", "end": "2015-10-31"}
    assert report.get("sampled_profile_dates") == 15
    assert sorted(report.get("calibrated_parameters", {}).keys()) == sorted(PARAM_KEYS)

    nml_params = read_nml_params()
    for key in PARAM_KEYS:
        assert abs(report["calibrated_parameters"][key] - nml_params[key]) <= 1e-9

    run_model()
    expected = compute_expected_metrics()

    assert report["event_dates"] == expected["event_dates"]
    assert report["thermocline_depth_metrics"]["matched_profile_count"] == 12
    assert report["thermocline_depth_metrics"] == expected["thermocline_depth_metrics"]
    assert abs(report["surface_bottom_delta_rmse_c"] - expected["surface_bottom_delta_rmse_c"]) <= 1e-6
    assert report["thermocline_depth_comparison"] == expected["comparison"]

    assert report["event_dates"]["simulated_onset"] == report["event_dates"]["observed_onset"]
    assert report["event_dates"]["simulated_breakdown"] == report["event_dates"]["observed_breakdown"]
    assert report["thermocline_depth_metrics"]["mean_abs_error_m"] <= 0.35 + 1e-9
    assert report["thermocline_depth_metrics"]["max_abs_error_m"] <= 0.80 + 1e-9
    assert report["surface_bottom_delta_rmse_c"] <= 0.18 + 1e-9


def test_model_output_window():
    run_model()
    output = pd.read_csv(OUTPUT_PATH)
    output["date"] = output["date"].astype(str)
    unique_dates = sorted(output["date"].unique().tolist())

    assert unique_dates[0] == "2015-04-01"
    assert unique_dates[-1] == "2015-10-31"
    assert len(unique_dates) == 214
