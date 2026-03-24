import json
from pathlib import Path

import numpy as np


def find_summary():
    candidates = [
        Path("/root/grid_forecast_summary.json"),
        Path("grid_forecast_summary.json"),
        Path(__file__).resolve().parent.parent / "grid_forecast_summary.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = list(Path(".").rglob("grid_forecast_summary.json"))
    if matches:
        return matches[0]
    return candidates[0]


SUMMARY_PATH = find_summary()


def load_summary():
    if not SUMMARY_PATH.exists():
        raise AssertionError(f"grid_forecast_summary.json not found at {SUMMARY_PATH}")
    with open(SUMMARY_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def test_summary_exists():
    assert SUMMARY_PATH.exists(), f"missing summary file: {SUMMARY_PATH}"


def test_top_level_schema():
    summary = load_summary()
    for key in ["dataset", "baseline", "mhc", "flow_diagnostics"]:
        assert key in summary, f"missing top-level key: {key}"


def test_dataset_schema():
    dataset = load_summary()["dataset"]
    assert dataset["lookback"] == 72
    assert dataset["horizon"] == 24
    assert dataset["num_features"] >= 8
    assert dataset["train_windows"] > 1000
    assert dataset["val_windows"] > 250
    assert dataset["target"] == "load_mw"
    assert "load_mw" in dataset["feature_names"]


def test_variant_metrics_present():
    summary = load_summary()
    required = [
        "mae",
        "rmse",
        "tail_mae",
        "tail_rmse",
        "grad_norm_mean",
        "grad_norm_std",
        "grad_norm_cv",
        "max_grad_norm",
        "steps",
    ]
    for section in ["baseline", "mhc"]:
        report = summary[section]
        for key in required:
            assert key in report, f"missing {section}.{key}"
            assert isinstance(report[key], (int, float)), f"{section}.{key} should be numeric"
        assert report["steps"] >= 160


def test_forecast_quality_reasonable():
    summary = load_summary()
    assert summary["baseline"]["mae"] < 15.0
    assert summary["baseline"]["rmse"] < 18.0
    assert summary["mhc"]["mae"] < 14.0
    assert summary["mhc"]["rmse"] < 17.0
    assert summary["mhc"]["tail_mae"] <= summary["baseline"]["tail_mae"] * 1.05
    assert summary["mhc"]["tail_rmse"] <= summary["baseline"]["tail_rmse"] * 1.05


def test_gradient_dispersion_improves():
    summary = load_summary()
    assert summary["mhc"]["grad_norm_cv"] < summary["baseline"]["grad_norm_cv"]
    assert summary["mhc"]["grad_norm_std"] <= summary["baseline"]["grad_norm_std"] * 1.1
    assert summary["mhc"]["max_grad_norm"] <= summary["baseline"]["max_grad_norm"] * 1.05


def test_flow_diagnostics_schema():
    flow = load_summary()["flow_diagnostics"]
    assert flow["num_streams"] == 4
    assert len(flow["labels"]) == len(flow["h_res_matrices"])
    assert len(flow["labels"]) >= 8
    assert flow["mean_row_abs_error"] < 0.08
    assert flow["mean_col_abs_error"] < 0.08
    assert flow["mean_offdiag_share"] > 0.02


def test_h_res_matrices_are_doubly_stochastic():
    matrices = load_summary()["flow_diagnostics"]["h_res_matrices"]
    for idx, matrix in enumerate(matrices):
        h_res = np.array(matrix, dtype=float)
        assert h_res.ndim == 2, f"H_res[{idx}] must be a matrix"
        assert h_res.shape[0] == h_res.shape[1], f"H_res[{idx}] must be square"
        assert h_res.shape[0] >= 3, f"H_res[{idx}] is unexpectedly small"
        assert np.all(h_res >= 0.0), f"H_res[{idx}] contains negative entries"

        row_sums = h_res.sum(axis=1)
        col_sums = h_res.sum(axis=0)
        assert np.allclose(row_sums, np.ones_like(row_sums), atol=0.12), f"H_res[{idx}] row sums invalid: {row_sums}"
        assert np.allclose(col_sums, np.ones_like(col_sums), atol=0.12), f"H_res[{idx}] col sums invalid: {col_sums}"


def test_h_res_not_all_identity():
    matrices = load_summary()["flow_diagnostics"]["h_res_matrices"]
    deviations = []
    for matrix in matrices:
        h_res = np.array(matrix, dtype=float)
        identity = np.eye(h_res.shape[0])
        deviations.append(float(np.abs(h_res - identity).max()))
    assert max(deviations) > 1e-3, "all H_res matrices stayed at identity"
