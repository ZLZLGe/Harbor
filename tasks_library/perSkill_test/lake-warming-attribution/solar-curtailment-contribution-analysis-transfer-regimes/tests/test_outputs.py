import json
import math
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_PATH = Path("/root/output/curtailment_regime_attribution.json")
DATA_DIR = Path("/root/data")

GROUPS = {
    "Weather": ["IrradianceWm2", "CloudCoverPct"],
    "DemandAbsorption": ["LocalLoadMW", "StorageAbsorptionMW"],
    "MaintenanceAvailability": ["ThermalAvailabilityPct", "OutageSharePct"],
    "ExportCongestion": ["InterfaceLoadingPct", "ExportPriceSpreadUsdMWh"],
}

TARGET_REGIMES = ["export_constrained", "balanced"]


def calc_r2(predictors: np.ndarray, response: np.ndarray) -> float:
    predictors = np.asarray(predictors, dtype=float)
    if predictors.ndim == 1:
        predictors = predictors[:, None]
    design = np.column_stack([np.ones(len(predictors)), predictors])
    coefficients, *_ = np.linalg.lstsq(design, response, rcond=None)
    fitted = design @ coefficients
    ss_res = np.square(response - fitted).sum()
    ss_tot = np.square(response - response.mean()).sum()
    return 1.0 - ss_res / ss_tot


def expected_results():
    dispatch = pd.read_csv(DATA_DIR / "dispatch_blocks.csv")
    weather = pd.read_csv(DATA_DIR / "weather_block.csv")
    load_absorption = pd.read_csv(DATA_DIR / "load_absorption_block.csv")
    maintenance = pd.read_csv(DATA_DIR / "maintenance_availability_block.csv")
    export = pd.read_csv(DATA_DIR / "export_congestion_block.csv")

    df = (
        dispatch.merge(weather, on="BlockHour")
        .merge(load_absorption, on="BlockHour")
        .merge(maintenance, on="BlockHour")
        .merge(export, on="BlockHour")
        .sort_values("BlockHour")
        .reset_index(drop=True)
    )

    feature_columns = [column for columns in GROUPS.values() for column in columns]
    results = {}

    for regime in TARGET_REGIMES:
        subset = df[df["operating_regime"] == regime].copy()
        X = subset[feature_columns].to_numpy(dtype=float)
        X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=0)
        y = subset["CurtailmentMWh"].to_numpy(dtype=float)

        u, singular_values, vt = np.linalg.svd(X, full_matrices=False)
        scores = u[:, :4] * singular_values[:4]
        loadings = pd.DataFrame(
            vt[:4].T,
            index=feature_columns,
            columns=[f"PC{i}" for i in range(1, 5)],
        )

        strength = np.zeros((4, 4), dtype=float)
        for group_index, (_, columns) in enumerate(GROUPS.items()):
            for component_index, component_name in enumerate(loadings.columns):
                strength[group_index, component_index] = loadings.loc[columns, component_name].abs().sum()

        best_assignment = None
        best_strength = -1.0
        for assignment in permutations(range(4)):
            total_strength = sum(strength[group_index, assignment[group_index]] for group_index in range(4))
            if total_strength > best_strength:
                best_strength = total_strength
                best_assignment = assignment

        ordered_scores = np.column_stack([scores[:, best_assignment[group_index]] for group_index in range(4)])
        full_r2 = calc_r2(ordered_scores, y)

        decreases = {}
        for group_index, group_name in enumerate(GROUPS):
            keep_columns = [index for index in range(4) if index != group_index]
            reduced_r2 = calc_r2(ordered_scores[:, keep_columns], y)
            decreases[group_name] = max(0.0, full_r2 - reduced_r2)

        total_positive_decrease = sum(decreases.values())
        normalized = {
            group_name: round(decrease / total_positive_decrease * 100.0, 1)
            for group_name, decrease in decreases.items()
        }
        dominant_group = max(normalized, key=normalized.get)
        results[regime] = {
            "dominant_driver": dominant_group,
            "normalized_contribution_pct": normalized[dominant_group],
        }

    return results


def test_output_contract_and_values():
    assert OUTPUT_PATH.exists(), "curtailment_regime_attribution.json not found"

    with OUTPUT_PATH.open("r") as handle:
        payload = json.load(handle)

    assert isinstance(payload, dict), "top-level JSON must be an object"
    assert set(payload.keys()) == set(TARGET_REGIMES), "output must contain exactly the two required regimes"

    expected = expected_results()
    for regime in TARGET_REGIMES:
        result = payload[regime]
        assert isinstance(result, dict), f"{regime} value must be an object"
        assert set(result.keys()) == {"dominant_driver", "normalized_contribution_pct"}, (
            f"{regime} object must contain only dominant_driver and normalized_contribution_pct"
        )
        assert result["dominant_driver"] in GROUPS, f"{regime} dominant_driver is invalid"

        contribution = float(result["normalized_contribution_pct"])
        assert 0.0 <= contribution <= 100.0, f"{regime} normalized contribution must be within 0-100"
        assert math.isclose(contribution, round(contribution, 1), abs_tol=1e-9), (
            f"{regime} contribution must keep one decimal place"
        )

        assert result["dominant_driver"] == expected[regime]["dominant_driver"], (
            f"{regime} dominant driver does not match expected result"
        )
        assert abs(contribution - expected[regime]["normalized_contribution_pct"]) <= 0.1, (
            f"{regime} normalized contribution does not match expected result"
        )
