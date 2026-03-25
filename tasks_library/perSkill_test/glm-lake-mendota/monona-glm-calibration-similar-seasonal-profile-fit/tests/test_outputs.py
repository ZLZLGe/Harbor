import json
import math
import os
import re
import subprocess
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
RESULT_PATH = TASK_ROOT / "results" / "monona_profile_calibration.json"
NML_PATH = TASK_ROOT / "glm3.nml"
OBS_PATH = TASK_ROOT / "inputs" / "monona_sparse_profiles.csv"
OUTPUT_PATH = TASK_ROOT / "output" / "monona_profiles.csv"
EXPECTED_PARAM_KEYS = ["Kw", "coef_mix_hyp", "wind_factor", "lw_factor", "ch"]


def read_nml_params():
    text = NML_PATH.read_text()
    params = {}
    for key in EXPECTED_PARAM_KEYS:
        match = re.search(rf"{key}\s*=\s*([-0-9.]+)", text)
        assert match, f"glm3.nml missing parameter {key}"
        params[key] = float(match.group(1))
    return params


def run_model():
    completed = subprocess.run(
        ["glm"],
        cwd=TASK_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert OUTPUT_PATH.exists(), "monona_profiles.csv was not generated"


def compute_metrics():
    observations = pd.read_csv(OBS_PATH)
    simulation = pd.read_csv(OUTPUT_PATH)
    merged = observations.merge(simulation, left_on=["sample_date", "depth_m"], right_on=["date", "depth_m"])
    assert not merged.empty, "No overlapping observation/simulation rows"
    merged["sq_error"] = (merged["temperature_c_x"] - merged["temperature_c_y"]) ** 2
    overall_rmse = math.sqrt(merged["sq_error"].mean())
    per_profile = (
        merged.groupby("sample_date")["sq_error"]
        .mean()
        .map(math.sqrt)
        .reset_index(name="rmse_c")
        .sort_values("sample_date")
        .reset_index(drop=True)
    )
    return overall_rmse, float(per_profile["rmse_c"].max()), per_profile


def main():
    assert RESULT_PATH.exists(), "Result JSON not found"
    with RESULT_PATH.open() as handle:
        result = json.load(handle)

    assert result.get("lake") == "Monona"
    assert result.get("simulation_window") == {"start": "2012-01-01", "end": "2013-12-31"}
    assert isinstance(result.get("profile_count"), int)
    assert result["profile_count"] == 11

    assert isinstance(result.get("calibrated_parameters"), dict)
    assert sorted(result["calibrated_parameters"].keys()) == sorted(EXPECTED_PARAM_KEYS)

    nml_params = read_nml_params()
    for key in EXPECTED_PARAM_KEYS:
        assert abs(result["calibrated_parameters"][key] - nml_params[key]) <= 1e-9

    run_model()
    overall_rmse, max_profile_rmse, per_profile = compute_metrics()

    assert overall_rmse <= 0.06 + 1e-9, f"overall RMSE too high: {overall_rmse:.6f}"
    assert max_profile_rmse <= 0.08 + 1e-9, f"max profile RMSE too high: {max_profile_rmse:.6f}"

    assert abs(result["overall_rmse_c"] - round(overall_rmse, 6)) <= 1e-6
    assert abs(result["max_profile_rmse_c"] - round(max_profile_rmse, 6)) <= 1e-6

    reported_profiles = result.get("profile_rmse_c")
    assert isinstance(reported_profiles, list)
    assert len(reported_profiles) == 11

    expected_profile_map = {
        row.sample_date: round(float(row.rmse_c), 6)
        for row in per_profile.itertuples(index=False)
    }
    reported_profile_map = {item["sample_date"]: item["rmse_c"] for item in reported_profiles}
    assert set(reported_profile_map) == set(expected_profile_map)
    for sample_date, expected_rmse in expected_profile_map.items():
        assert abs(reported_profile_map[sample_date] - expected_rmse) <= 2e-6


if __name__ == "__main__":
    main()
