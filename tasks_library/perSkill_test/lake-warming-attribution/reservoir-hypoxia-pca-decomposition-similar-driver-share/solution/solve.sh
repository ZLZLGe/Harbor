#!/bin/bash
set -e

python3 <<'PY'
import numpy as np
import pandas as pd


DATA_PATH = "/root/data/summer_hypoxia_panel.csv"
OUTPUT_PATH = "/root/output/hypoxia_driver_share.csv"

DRIVER_COLUMNS = [
    "surface_temp_c",
    "stratification_days",
    "schmidt_stability",
    "residence_time_days",
    "drawdown_m",
    "flushing_ratio",
    "tp_load_t",
    "srf_p_mg_l",
    "chlorophyll_a_ug_l",
    "bulkhead_pct",
    "dock_density_km",
    "impervious_shoreline_ha",
]

CATEGORY_COLUMNS = {
    "Thermal": ["surface_temp_c", "stratification_days", "schmidt_stability"],
    "Flow": ["residence_time_days", "drawdown_m", "flushing_ratio"],
    "Nutrient": ["tp_load_t", "srf_p_mg_l", "chlorophyll_a_ug_l"],
    "Shoreline": ["bulkhead_pct", "dock_density_km", "impervious_shoreline_ha"],
}


def standardize(frame, columns):
    values = frame[columns].to_numpy(dtype=float)
    return (values - values.mean(axis=0)) / values.std(axis=0, ddof=0)


def varimax(phi, gamma=1.0, q=100, tol=1e-7):
    p, k = phi.shape
    rotation = np.eye(k)
    previous = 0.0
    for _ in range(q):
        rotated = phi @ rotation
        basis, singular, vh = np.linalg.svd(
            phi.T
            @ (
                rotated**3
                - (gamma / p) * rotated @ np.diag(np.sum(rotated**2, axis=0))
            ),
            full_matrices=False,
        )
        rotation = basis @ vh
        current = singular.sum()
        if previous and current - previous < tol:
            break
        previous = current
    return phi @ rotation, rotation


def calc_r2(matrix, target):
    if matrix.size == 0:
        design = np.ones((len(target), 1))
    else:
        design = np.column_stack([np.ones(len(target)), matrix])
    beta = np.linalg.lstsq(design, target, rcond=None)[0]
    fitted = design @ beta
    ss_res = np.sum((target - fitted) ** 2)
    ss_tot = np.sum((target - target.mean()) ** 2)
    return 1 - ss_res / ss_tot


df = pd.read_csv(DATA_PATH)
X = standardize(df, DRIVER_COLUMNS)
y = df["summer_hypoxia_days"].to_numpy(dtype=float)

u, singular, vh = np.linalg.svd(X, full_matrices=False)
n_factors = 4
loadings = vh[:n_factors].T * singular[:n_factors] / np.sqrt(len(df) - 1)
rotated_loadings, rotation = varimax(loadings)
scores = (u[:, :n_factors] * singular[:n_factors]) @ rotation

column_index = {name: idx for idx, name in enumerate(DRIVER_COLUMNS)}
factor_to_category = {}
for factor_idx in range(n_factors):
    factor_to_category[factor_idx] = max(
        CATEGORY_COLUMNS,
        key=lambda category: np.abs(
            rotated_loadings[
                [column_index[col] for col in CATEGORY_COLUMNS[category]],
                factor_idx,
            ]
        ).mean(),
    )

full_r2 = calc_r2(scores, y)
raw_contributions = {}
for category in CATEGORY_COLUMNS:
    factor_ids = [
        idx for idx, mapped_category in factor_to_category.items()
        if mapped_category == category
    ]
    keep_ids = [idx for idx in range(n_factors) if idx not in factor_ids]
    raw_contributions[category] = max(full_r2 - calc_r2(scores[:, keep_ids], y), 0.0)

total_contribution = sum(raw_contributions.values())
share_pct = {
    category: 100.0 * value / total_contribution
    for category, value in raw_contributions.items()
}

dominant_category = max(share_pct, key=share_pct.get)
result = pd.DataFrame(
    [{"category": dominant_category, "share_pct": round(share_pct[dominant_category], 2)}]
)
result.to_csv(OUTPUT_PATH, index=False)
PY
