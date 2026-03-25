import os
import subprocess
from pathlib import Path

import pandas as pd


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
OBS_PATH = TASK_ROOT / "inputs" / "release_temperature_observed.csv"
FIT_PATH = TASK_ROOT / "reports" / "release_temperature_fit.csv"
MODEL_OUTPUT_PATH = TASK_ROOT / "output" / "release_temperature_daily.csv"
EXPECTED_COLUMNS = [
    "date",
    "observed_release_temp_c",
    "simulated_release_temp_c",
    "abs_error_c",
]


def run_model():
    completed = subprocess.run(
        ["glm"],
        cwd=TASK_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "TASK_ROOT": str(TASK_ROOT)},
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert MODEL_OUTPUT_PATH.exists(), "release_temperature_daily.csv was not generated"


def read_fit():
    assert FIT_PATH.exists(), "release_temperature_fit.csv not found"
    fit = pd.read_csv(FIT_PATH)
    assert list(fit.columns) == EXPECTED_COLUMNS
    return fit


def test_fit_file_contract():
    observations = pd.read_csv(OBS_PATH)
    fit = read_fit()

    assert len(fit) == len(observations) == 100
    assert fit["date"].tolist() == sorted(fit["date"].tolist())
    assert fit["date"].is_unique
    assert fit["date"].tolist() == observations["date"].tolist()

    merged = observations.merge(fit, on="date", how="inner")
    assert len(merged) == len(observations)
    diff = (merged["observed_release_temp_c_x"] - merged["observed_release_temp_c_y"]).abs().max()
    assert diff <= 5e-4, f"observed series mismatch: {diff}"

    expected_abs_error = (merged["simulated_release_temp_c"] - merged["observed_release_temp_c_x"]).abs()
    abs_error_diff = (expected_abs_error - merged["abs_error_c"]).abs().max()
    assert abs_error_diff <= 5e-4, f"abs_error_c mismatch: {abs_error_diff}"


def test_model_output_reproduces_report():
    fit = read_fit()
    run_model()

    simulated = pd.read_csv(MODEL_OUTPUT_PATH)[["date", "simulated_release_temp_c"]]
    merged = fit.merge(simulated, on="date", suffixes=("_report", "_rerun"))
    assert len(merged) == len(fit)

    max_delta = (merged["simulated_release_temp_c_report"] - merged["simulated_release_temp_c_rerun"]).abs().max()
    assert max_delta <= 5e-4, f"fit CSV does not match rerun output: {max_delta}"


def test_error_thresholds():
    observations = pd.read_csv(OBS_PATH)
    fit = read_fit()
    merged = observations.merge(fit, on="date", how="inner")
    errors = merged["simulated_release_temp_c"] - merged["observed_release_temp_c_x"]

    rmse = float((errors.pow(2).mean()) ** 0.5)
    max_abs_error = float(errors.abs().max())
    mean_bias = float(errors.mean())

    assert rmse <= 0.08 + 1e-9, f"RMSE too high: {rmse:.6f}"
    assert max_abs_error <= 0.18 + 1e-9, f"max absolute error too high: {max_abs_error:.6f}"
    assert abs(mean_bias) <= 0.05 + 1e-9, f"mean bias too high: {mean_bias:.6f}"
