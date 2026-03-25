import csv
import math
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_PATH = Path("/root/output/dominant_bloom_driver.csv")
DATA_DIR = Path("/root/data")

GROUPS = {
    "Meteorology": ["SurfaceTempAnomaly", "SunlightHours"],
    "Nutrient": ["TPLoad", "TNLoad"],
    "Hydrodynamics": ["ResidenceDays", "MixingDepth"],
    "Shoreline": ["ImperviousPct", "DockDensity"],
}


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


def expected_result():
    bloom = pd.read_csv(DATA_DIR / "annual_bloom.csv")
    meteorology = pd.read_csv(DATA_DIR / "reservoir_meteorology.csv")
    nutrients = pd.read_csv(DATA_DIR / "reservoir_nutrients.csv")
    hydrodynamics = pd.read_csv(DATA_DIR / "reservoir_hydrodynamics.csv")
    shoreline = pd.read_csv(DATA_DIR / "shoreline_development.csv")

    df = (
        bloom.merge(meteorology, on="WaterYear")
        .merge(nutrients, on="WaterYear")
        .merge(hydrodynamics, on="WaterYear")
        .merge(shoreline, on="WaterYear")
        .sort_values("WaterYear")
        .reset_index(drop=True)
    )

    feature_columns = [column for columns in GROUPS.values() for column in columns]
    X = df[feature_columns].to_numpy(dtype=float)
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=0)
    y = df["BloomSeverityIndex"].to_numpy(dtype=float)

    u, singular_values, vt = np.linalg.svd(X, full_matrices=False)
    scores = u[:, :4] * singular_values[:4]
    loadings = pd.DataFrame(
        vt[:4].T,
        index=feature_columns,
        columns=[f"PC{i}" for i in range(1, 5)],
    )

    component_names = list(loadings.columns)
    strength = np.zeros((4, 4), dtype=float)
    for group_index, (_, columns) in enumerate(GROUPS.items()):
        for component_index, component_name in enumerate(component_names):
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
    return dominant_group, normalized[dominant_group]


def main():
    assert OUTPUT_PATH.exists(), "dominant_bloom_driver.csv not found"

    with OUTPUT_PATH.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == ["driver_category", "normalized_contribution_pct"], "unexpected columns"

    assert len(rows) == 1, "output must contain exactly one data row"

    row = rows[0]
    assert row["driver_category"] in GROUPS, "unexpected driver category"

    actual_value = float(row["normalized_contribution_pct"])
    assert 0.0 <= actual_value <= 100.0, "normalized contribution must be within 0-100"
    assert math.isclose(actual_value, round(actual_value, 1), abs_tol=1e-9), "value must keep one decimal place"

    expected_category, expected_value = expected_result()
    assert row["driver_category"] == expected_category, "dominant category is incorrect"
    assert abs(actual_value - expected_value) <= 0.1, "normalized contribution does not match expected result"


if __name__ == "__main__":
    main()
