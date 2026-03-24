import os
import re
import subprocess

import numpy as np
import pandas as pd
import pytest
from netCDF4 import Dataset

SIM_ROOT = "/root"
NML_PATH = os.path.join(SIM_ROOT, "glm3.nml")
REF_PATH = os.path.join(SIM_ROOT, "manual_thermocline_reference.csv")
NC_PATH = os.path.join(SIM_ROOT, "output", "output.nc")
REPORT_PATH = os.path.join(SIM_ROOT, "output", "thermocline_tracking.csv")
WINDOW_START = pd.Timestamp("2013-04-29")
WINDOW_END = pd.Timestamp("2013-10-29")
GRADIENT_THRESHOLD = 1.0
MIN_DEPTH = 2.0
MAX_DEPTH = 20.0
TARGET_COVERAGE = 0.75
TARGET_MAE = 3.5
TARGET_MAX_ABS = 7.0
TARGET_VALID_MODEL_DAYS = 95


def parse_nml_value(name, text):
    match = re.search(rf"{name}\s*=\s*'([^']+)'", text)
    if match:
        return match.group(1)
    match = re.search(rf"{name}\s*=\s*([-+0-9.eE]+)", text)
    if match:
        return float(match.group(1))
    raise ValueError(f"Missing {name} in glm3.nml")


NML_TEXT = open(NML_PATH, "r").read()
START_TIME = pd.Timestamp(parse_nml_value("start", NML_TEXT))
LAKE_DEPTH = float(parse_nml_value("lake_depth", NML_TEXT))


def read_reference():
    ref = pd.read_csv(REF_PATH, parse_dates=["date", "observation_time"]).sort_values("date")
    ref["manual_stratified"] = ref["manual_stratified"].astype(str).str.lower() == "true"
    ref["reference_available"] = 1
    ref["reference_stratified"] = ref["manual_stratified"].astype(int)
    ref["reference_thermocline_depth_m"] = ref["manual_thermocline_depth_m"]
    return ref.reset_index(drop=True)


def detect_daily_thermocline():
    nc = Dataset(NC_PATH, "r")
    time = nc.variables["time"][:]
    z = nc.variables["z"][:]
    temp = nc.variables["temp"][:]
    rows = []
    for t_idx in range(len(time)):
        timestamp = START_TIME + pd.Timedelta(hours=float(time[t_idx]))
        day = timestamp.floor("D")
        if day < WINDOW_START or day > WINDOW_END:
            continue

        layers = []
        heights = z[t_idx, :, 0, 0]
        temps = temp[t_idx, :, 0, 0]
        for layer_idx in range(len(heights)):
            h_val = heights[layer_idx]
            t_val = temps[layer_idx]
            if np.ma.is_masked(h_val) or np.ma.is_masked(t_val):
                continue
            depth = LAKE_DEPTH - float(h_val)
            if 0 <= depth <= LAKE_DEPTH:
                layers.append((depth, float(t_val)))

        if len(layers) < 2:
            rows.append(
                {
                    "date": day,
                    "model_stratified": 0,
                    "model_thermocline_depth_m": np.nan,
                    "model_max_gradient_c_per_m": np.nan,
                }
            )
            continue

        layers.sort(key=lambda item: item[0])
        best = None
        for (depth_a, temp_a), (depth_b, temp_b) in zip(layers, layers[1:]):
            delta_depth = depth_b - depth_a
            if delta_depth <= 0:
                continue
            gradient = (temp_a - temp_b) / delta_depth
            midpoint = (depth_a + depth_b) / 2.0
            candidate = (gradient, midpoint)
            if best is None or candidate[0] > best[0] or (
                candidate[0] == best[0] and candidate[1] < best[1]
            ):
                best = candidate

        if best is None:
            max_gradient = np.nan
            stratified = 0
            thermocline_depth = np.nan
        else:
            max_gradient, midpoint = best
            stratified = int(
                max_gradient >= GRADIENT_THRESHOLD and MIN_DEPTH <= midpoint <= MAX_DEPTH
            )
            thermocline_depth = midpoint if stratified else np.nan

        rows.append(
            {
                "date": day,
                "model_stratified": stratified,
                "model_thermocline_depth_m": thermocline_depth,
                "model_max_gradient_c_per_m": max_gradient,
            }
        )

    nc.close()
    tracking = pd.DataFrame(rows).sort_values("date").drop_duplicates("date", keep="first")
    full_dates = pd.DataFrame({"date": pd.date_range(WINDOW_START, WINDOW_END, freq="D")})
    tracking = full_dates.merge(tracking, on="date", how="left")
    tracking["model_stratified"] = tracking["model_stratified"].fillna(0).astype(int)
    return tracking


def build_expected_report():
    tracking = detect_daily_thermocline()
    ref = read_reference()
    expected = tracking.merge(
        ref[
            [
                "date",
                "reference_available",
                "reference_stratified",
                "reference_thermocline_depth_m",
            ]
        ],
        on="date",
        how="left",
    )
    expected["reference_available"] = expected["reference_available"].fillna(0).astype(int)
    expected["reference_stratified"] = expected["reference_stratified"].fillna(0).astype(int)
    expected["depth_error_m"] = (
        expected["model_thermocline_depth_m"] - expected["reference_thermocline_depth_m"]
    )
    expected["abs_depth_error_m"] = expected["depth_error_m"].abs()

    numeric_cols = [
        "model_thermocline_depth_m",
        "model_max_gradient_c_per_m",
        "reference_thermocline_depth_m",
        "depth_error_m",
        "abs_depth_error_m",
    ]
    expected[numeric_cols] = expected[numeric_cols].round(4)
    expected["date"] = expected["date"].dt.strftime("%Y-%m-%d")
    return expected[
        [
            "date",
            "model_stratified",
            "model_thermocline_depth_m",
            "model_max_gradient_c_per_m",
            "reference_available",
            "reference_stratified",
            "reference_thermocline_depth_m",
            "depth_error_m",
            "abs_depth_error_m",
        ]
    ]


class TestThermoclineTracking:
    def test_glm_runs(self):
        result = subprocess.run(["glm"], cwd=SIM_ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr or result.stdout

    def test_output_files_exist(self):
        assert os.path.exists(NC_PATH), "output.nc not found"
        assert os.path.exists(REPORT_PATH), "thermocline_tracking.csv not found"

    def test_tracking_matches_expected(self):
        actual = pd.read_csv(REPORT_PATH)
        expected = build_expected_report()

        assert list(actual.columns) == list(expected.columns)
        assert len(actual) == 184
        assert actual["date"].iloc[0] == "2013-04-29"
        assert actual["date"].iloc[-1] == "2013-10-29"
        pd.testing.assert_frame_equal(actual, expected, check_dtype=False, atol=1e-4, rtol=0)

    def test_coverage_and_error_thresholds(self):
        tracking = pd.read_csv(REPORT_PATH)
        ref_mask = (tracking["reference_available"] == 1) & (tracking["reference_stratified"] == 1)
        matched = tracking.loc[ref_mask & (tracking["model_stratified"] == 1)].copy()

        coverage = len(matched) / int(ref_mask.sum())
        mae = float(matched["abs_depth_error_m"].mean())
        max_abs = float(matched["abs_depth_error_m"].max())
        valid_model_days = int(tracking["model_stratified"].sum())

        assert int(tracking["reference_available"].sum()) == 12
        assert int(ref_mask.sum()) == 9
        assert valid_model_days >= TARGET_VALID_MODEL_DAYS, (
            f"Only {valid_model_days} stratified model days, expected at least {TARGET_VALID_MODEL_DAYS}"
        )
        assert coverage >= TARGET_COVERAGE, (
            f"Matched reference coverage {coverage:.4f} < {TARGET_COVERAGE:.2f}"
        )
        assert mae < TARGET_MAE, f"MAE {mae:.4f} >= {TARGET_MAE:.1f}"
        assert max_abs < TARGET_MAX_ABS, f"Max abs depth error {max_abs:.4f} >= {TARGET_MAX_ABS:.1f}"
