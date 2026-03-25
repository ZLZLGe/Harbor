import json
import re
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from netCDF4 import Dataset

REPORT_PATH = "/root/reports/temperature_alignment_report.json"
NML_PATH = "/root/config/glm3.nml"
NC_PATH = "/root/data/mendota_stratified_output.nc"
OBS_PATH = "/root/data/alignment_observations.csv"
SURFACE_MAX_DEPTH = 5
DEEP_MIN_DEPTH = 15


def read_nml_value(text: str, key: str) -> str:
    match = re.search(rf"{key}\s*=\s*'([^']+)'", text)
    if match:
        return match.group(1)
    match = re.search(rf"{key}\s*=\s*([-+]?[0-9]*\.?[0-9]+)", text)
    if not match:
        raise ValueError(f"missing {key} in glm3.nml")
    return match.group(1)


def load_config():
    text = open(NML_PATH, "r", encoding="utf-8").read()
    start = pd.Timestamp(datetime.strptime(read_nml_value(text, "start"), "%Y-%m-%d %H:%M:%S"))
    lake_depth = float(read_nml_value(text, "lake_depth"))
    return start, lake_depth


def load_simulation(start: pd.Timestamp, lake_depth: float) -> pd.DataFrame:
    with Dataset(NC_PATH, "r") as ds:
        times = ds.variables["time"][:]
        z = ds.variables["z"][:]
        temp = ds.variables["temp"][:]

    records = []
    for t_idx, hour_offset in enumerate(times):
        dt = start + pd.Timedelta(hours=float(hour_offset))
        heights = z[t_idx, :, 0, 0]
        temps = temp[t_idx, :, 0, 0]
        for height, temp_value in zip(heights, temps):
            if np.ma.is_masked(height) or np.ma.is_masked(temp_value):
                continue
            rounded_depth = int(round(lake_depth - float(height)))
            if 0 <= rounded_depth <= lake_depth:
                records.append(
                    {
                        "datetime": dt,
                        "depth_rounded_m": rounded_depth,
                        "temp_sim": float(temp_value),
                    }
                )

    return (
        pd.DataFrame(records)
        .groupby(["datetime", "depth_rounded_m"], as_index=False)["temp_sim"]
        .mean()
    )


def load_observations() -> pd.DataFrame:
    obs = pd.read_csv(OBS_PATH)
    obs["datetime"] = pd.to_datetime(obs["datetime"])
    obs["depth_rounded_m"] = obs["depth"].round().astype(int)
    return obs.rename(columns={"temp": "temp_obs"})[
        ["datetime", "depth_rounded_m", "temp_obs"]
    ]


def calculate_expected():
    start, lake_depth = load_config()
    sim = load_simulation(start, lake_depth)
    obs = load_observations()
    matched = obs.merge(sim, on=["datetime", "depth_rounded_m"], how="inner")
    matched["error"] = matched["temp_sim"] - matched["temp_obs"]
    surface = matched[matched["depth_rounded_m"] <= SURFACE_MAX_DEPTH]
    deep = matched[matched["depth_rounded_m"] >= DEEP_MIN_DEPTH]

    return {
        "lake_depth_m": lake_depth,
        "surface_max_depth_m": float(SURFACE_MAX_DEPTH),
        "deep_min_depth_m": float(DEEP_MIN_DEPTH),
        "valid_match_count": int(len(matched)),
        "total_rmse_c": float(np.sqrt(np.mean(np.square(matched["error"])))),
        "surface_rmse_c": float(np.sqrt(np.mean(np.square(surface["error"])))),
        "deep_rmse_c": float(np.sqrt(np.mean(np.square(deep["error"])))),
        "mean_bias_c": float(matched["error"].mean()),
    }


def test_report_exists():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
    assert isinstance(report, dict)


def test_report_fields_and_values():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    expected = calculate_expected()
    required_keys = [
        "lake_depth_m",
        "surface_max_depth_m",
        "deep_min_depth_m",
        "valid_match_count",
        "total_rmse_c",
        "surface_rmse_c",
        "deep_rmse_c",
        "mean_bias_c",
    ]

    for key in required_keys:
        assert key in report, f"missing key: {key}"

    assert isinstance(report["valid_match_count"], int)
    for key in required_keys:
        if key != "valid_match_count":
            assert isinstance(report[key], (int, float)), f"{key} must be numeric"

    assert report["valid_match_count"] == expected["valid_match_count"]
    assert report["lake_depth_m"] == pytest.approx(expected["lake_depth_m"], abs=1e-6)
    assert report["surface_max_depth_m"] == pytest.approx(expected["surface_max_depth_m"], abs=1e-6)
    assert report["deep_min_depth_m"] == pytest.approx(expected["deep_min_depth_m"], abs=1e-6)
    assert report["total_rmse_c"] == pytest.approx(expected["total_rmse_c"], abs=5e-4)
    assert report["surface_rmse_c"] == pytest.approx(expected["surface_rmse_c"], abs=5e-4)
    assert report["deep_rmse_c"] == pytest.approx(expected["deep_rmse_c"], abs=5e-4)
    assert report["mean_bias_c"] == pytest.approx(expected["mean_bias_c"], abs=5e-4)
