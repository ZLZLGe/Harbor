#!/bin/bash
set -euo pipefail

python3 <<'PY'
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd

data_dir = Path("/root/data")
output_dir = Path("/root/output")
output_dir.mkdir(parents=True, exist_ok=True)

bloom = pd.read_csv(data_dir / "annual_bloom.csv")
meteorology = pd.read_csv(data_dir / "reservoir_meteorology.csv")
nutrients = pd.read_csv(data_dir / "reservoir_nutrients.csv")
hydrodynamics = pd.read_csv(data_dir / "reservoir_hydrodynamics.csv")
shoreline = pd.read_csv(data_dir / "shoreline_development.csv")

df = (
    bloom.merge(meteorology, on="WaterYear")
    .merge(nutrients, on="WaterYear")
    .merge(hydrodynamics, on="WaterYear")
    .merge(shoreline, on="WaterYear")
    .sort_values("WaterYear")
    .reset_index(drop=True)
)

groups = {
    "Meteorology": ["SurfaceTempAnomaly", "SunlightHours"],
    "Nutrient": ["TPLoad", "TNLoad"],
    "Hydrodynamics": ["ResidenceDays", "MixingDepth"],
    "Shoreline": ["ImperviousPct", "DockDensity"],
}

feature_columns = [column for columns in groups.values() for column in columns]
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
for group_index, (_, columns) in enumerate(groups.items()):
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

full_r2 = calc_r2(ordered_scores, y)
decreases = {}
for group_index, group_name in enumerate(groups):
    keep_columns = [index for index in range(4) if index != group_index]
    reduced_r2 = calc_r2(ordered_scores[:, keep_columns], y)
    decreases[group_name] = max(0.0, full_r2 - reduced_r2)

total_positive_decrease = sum(decreases.values())
normalized = {
    group_name: round(decrease / total_positive_decrease * 100.0, 1)
    for group_name, decrease in decreases.items()
}
dominant_group = max(normalized, key=normalized.get)

pd.DataFrame(
    [
        {
            "driver_category": dominant_group,
            "normalized_contribution_pct": normalized[dominant_group],
        }
    ]
).to_csv(output_dir / "dominant_bloom_driver.csv", index=False)
PY
