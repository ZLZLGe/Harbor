import json
import os
import re
import subprocess
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
GLM_BIN = os.environ.get("GLM_BIN", "glm")
NML_PATH = TASK_ROOT / "glm3.nml"
OBS_PATH = TASK_ROOT / "inputs" / "observed_under_ice_profiles.csv"
TARGETS_PATH = TASK_ROOT / "inputs" / "ice_event_targets.json"
OUTPUT_PATH = TASK_ROOT / "output" / "under_ice_profiles.csv"
REPORT_PATH = TASK_ROOT / "analysis" / "under_ice_fit_summary.json"
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
        [GLM_BIN],
        cwd=TASK_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "TASK_ROOT": str(TASK_ROOT)},
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert OUTPUT_PATH.exists(), "under_ice_profiles.csv was not generated"


def two_degree_isotherm_depth(profile_df):
    profile_df = profile_df.sort_values("depth_m").reset_index(drop=True)
    pairs = list(zip(profile_df["depth_m"], profile_df["temperature_c"]))
    for (depth_1, temp_1), (depth_2, temp_2) in zip(pairs[:-1], pairs[1:]):
        if abs(temp_1 - 2.0) <= 1e-12:
            return round(float(depth_1), 6)
        if (temp_1 - 2.0) * (temp_2 - 2.0) <= 0 and temp_1 != temp_2:
            fraction = (2.0 - temp_1) / (temp_2 - temp_1)
            return round(float(depth_1 + fraction * (depth_2 - depth_1)), 6)
    raise AssertionError("Could not locate 2.0C isotherm")


def compute_expected(report):
    observations = pd.read_csv(OBS_PATH)
    observations["sample_date"] = observations["sample_date"].astype(str)
    simulation = pd.read_csv(OUTPUT_PATH)
    simulation["date"] = simulation["date"].astype(str)

    merged = observations.merge(
        simulation,
        left_on=["sample_date", "depth_m"],
        right_on=["date", "depth_m"],
        how="inner",
        suffixes=("_obs", "_sim"),
    )
    assert not merged.empty, "No overlapping observation/simulation rows"
    merged["sq_error"] = (merged["temperature_c_obs"] - merged["temperature_c_sim"]) ** 2
    overall_rmse = round(float(merged["sq_error"].mean() ** 0.5), 6)

    sample_dates = sorted(observations["sample_date"].unique().tolist())
    comparison = []
    bottom_biases = []
    for sample_date in sample_dates:
        obs_profile = observations[observations["sample_date"] == sample_date].copy()
        sim_profile = simulation[simulation["date"] == sample_date].copy()
        observed_depth = two_degree_isotherm_depth(obs_profile.rename(columns={"sample_date": "date"}))
        simulated_depth = two_degree_isotherm_depth(sim_profile)
        observed_bottom = round(float(obs_profile.sort_values("depth_m").iloc[-1]["temperature_c"]), 6)
        simulated_bottom = round(float(sim_profile.sort_values("depth_m").iloc[-1]["temperature_c"]), 6)
        bottom_biases.append(abs(simulated_bottom - observed_bottom))
        comparison.append(
            {
                "sample_date": sample_date,
                "observed_depth_m": observed_depth,
                "simulated_depth_m": simulated_depth,
                "abs_error_m": round(abs(simulated_depth - observed_depth), 6),
                "observed_bottom_temp_c": observed_bottom,
                "simulated_bottom_temp_c": simulated_bottom,
            }
        )

    daily_rows = []
    for date_str, profile_df in simulation.groupby("date"):
        profile_df = profile_df.sort_values("depth_m").reset_index(drop=True)
        daily_rows.append(
            {
                "date": date_str,
                "surface_temp_c": float(profile_df.iloc[0]["temperature_c"]),
                "bottom_temp_c": float(profile_df.iloc[-1]["temperature_c"]),
                "ice_thickness_m": float(profile_df.iloc[0]["ice_thickness_m"]),
                "two_degree_isotherm_depth_m": two_degree_isotherm_depth(profile_df),
            }
        )
    daily_df = pd.DataFrame(daily_rows).sort_values("date").reset_index(drop=True)

    simulated_ice_onset = daily_df[daily_df["ice_thickness_m"] >= 0.05].iloc[0]["date"]
    simulated_stable_inverse_onset = daily_df[
        (daily_df["ice_thickness_m"] >= 0.05)
        & ((daily_df["bottom_temp_c"] - daily_df["surface_temp_c"]) >= 2.8)
        & (daily_df["two_degree_isotherm_depth_m"] >= 3.6)
    ].iloc[0]["date"]
    simulated_peak_ice_date = daily_df.loc[daily_df["ice_thickness_m"].idxmax(), "date"]

    return {
        "sampled_profile_dates": len(sample_dates),
        "fit_metrics": {
            "overall_profile_rmse_c": overall_rmse,
            "max_bottom_bias_c": round(max(bottom_biases), 6),
            "mean_abs_two_degree_isotherm_bias_m": round(
                sum(item["abs_error_m"] for item in comparison) / len(comparison),
                6,
            ),
            "max_abs_two_degree_isotherm_bias_m": round(
                max(item["abs_error_m"] for item in comparison),
                6,
            ),
        },
        "comparison": comparison,
        "key_dates": {
            "observed_ice_onset": report["key_dates"]["observed_ice_onset"],
            "simulated_ice_onset": str(simulated_ice_onset),
            "observed_stable_inverse_onset": report["key_dates"]["observed_stable_inverse_onset"],
            "simulated_stable_inverse_onset": str(simulated_stable_inverse_onset),
            "observed_peak_ice_date": report["key_dates"]["observed_peak_ice_date"],
            "simulated_peak_ice_date": str(simulated_peak_ice_date),
        },
    }


def main():
    assert REPORT_PATH.exists(), "under_ice_fit_summary.json not found"
    with REPORT_PATH.open() as handle:
        report = json.load(handle)

    targets = json.loads(TARGETS_PATH.read_text())
    assert report.get("lake") == "North Star Bay"
    assert report.get("simulation_window") == {"start": "2021-12-01", "end": "2022-03-15"}
    assert sorted(report.get("calibrated_parameters", {}).keys()) == sorted(PARAM_KEYS)

    nml_params = read_nml_params()
    for key in PARAM_KEYS:
        assert abs(report["calibrated_parameters"][key] - nml_params[key]) <= 1e-9

    assert report["key_dates"]["observed_ice_onset"] == targets["ice_onset_date"]
    assert report["key_dates"]["observed_stable_inverse_onset"] == targets["stable_inverse_onset_date"]
    assert report["key_dates"]["observed_peak_ice_date"] == targets["peak_ice_date"]

    run_model()
    expected = compute_expected(report)

    assert report["sampled_profile_dates"] == expected["sampled_profile_dates"]
    assert report["key_dates"] == expected["key_dates"]
    assert report["fit_metrics"] == expected["fit_metrics"]
    assert report["two_degree_isotherm_comparison"] == expected["comparison"]

    assert report["key_dates"]["simulated_ice_onset"] == report["key_dates"]["observed_ice_onset"]
    assert report["key_dates"]["simulated_stable_inverse_onset"] == report["key_dates"]["observed_stable_inverse_onset"]
    assert report["key_dates"]["simulated_peak_ice_date"] == report["key_dates"]["observed_peak_ice_date"]

    assert report["fit_metrics"]["overall_profile_rmse_c"] <= 0.02 + 1e-9
    assert report["fit_metrics"]["max_bottom_bias_c"] <= 0.02 + 1e-9
    assert report["fit_metrics"]["mean_abs_two_degree_isotherm_bias_m"] <= 0.02 + 1e-9
    assert report["fit_metrics"]["max_abs_two_degree_isotherm_bias_m"] <= 0.03 + 1e-9


if __name__ == "__main__":
    main()
