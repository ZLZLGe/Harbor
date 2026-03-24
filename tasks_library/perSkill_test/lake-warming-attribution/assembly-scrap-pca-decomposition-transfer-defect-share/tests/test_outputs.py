import csv
import os

import numpy as np
import pandas as pd


DATA_DIR = "/root/data"
OUTPUT_PATH = "/root/output/scrap_defect_share.csv"

CATEGORY_COLUMNS = {
    "Climate": ["ambient_temp_c", "ambient_humidity_pct", "dew_point_c"],
    "Vibration": ["spindle_vibration_mm_s", "fixture_shock_g", "bearing_temp_c"],
    "Material": ["incoming_thickness_cv", "supplier_mix_delta_pct", "burr_rate_pct"],
    "Load": ["cycle_time_sec", "overtime_minutes", "queue_length_units"],
}


def standardize(values):
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


def expected_answer():
    environment = pd.read_csv(f"{DATA_DIR}/line_environment.csv")
    machine = pd.read_csv(f"{DATA_DIR}/machine_condition.csv")
    material = pd.read_csv(f"{DATA_DIR}/incoming_material.csv")
    load = pd.read_csv(f"{DATA_DIR}/line_load.csv")
    quality = pd.read_csv(f"{DATA_DIR}/scrap_quality.csv")

    df = (
        environment.merge(machine, on="shift_id")
        .merge(material, on="shift_id")
        .merge(load, on="shift_id")
        .merge(quality, on="shift_id")
    )

    driver_columns = [column for columns in CATEGORY_COLUMNS.values() for column in columns]
    X = standardize(df[driver_columns].to_numpy(dtype=float))
    y = df["scrap_rate_pct"].to_numpy(dtype=float)

    u, singular, vh = np.linalg.svd(X, full_matrices=False)
    n_factors = 4
    loadings = vh[:n_factors].T * singular[:n_factors] / np.sqrt(len(df) - 1)
    rotated_loadings, rotation = varimax(loadings)
    scores = (u[:, :n_factors] * singular[:n_factors]) @ rotation

    column_index = {name: idx for idx, name in enumerate(driver_columns)}
    factor_to_category = {}
    for factor_idx in range(n_factors):
        factor_to_category[factor_idx] = max(
            CATEGORY_COLUMNS,
            key=lambda category: np.abs(
                rotated_loadings[
                    [column_index[column] for column in CATEGORY_COLUMNS[category]],
                    factor_idx,
                ]
            ).mean(),
        )

    design = np.column_stack([np.ones(len(df)), scores])
    beta = np.linalg.lstsq(design, y, rcond=None)[0][1:]

    raw_contributions = {category: 0.0 for category in CATEGORY_COLUMNS}
    for factor_idx, category in factor_to_category.items():
        raw_contributions[category] += abs(beta[factor_idx]) * scores[:, factor_idx].var(ddof=0)

    total_contribution = sum(raw_contributions.values())
    share_pct = {
        category: 100.0 * contribution / total_contribution
        for category, contribution in raw_contributions.items()
    }

    dominant_category = max(share_pct, key=share_pct.get)
    return dominant_category, share_pct[dominant_category]


class TestAssemblyScrapDriverShare:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), "scrap_defect_share.csv not found"

    def test_output_matches_reference_answer(self):
        expected_category, expected_share = expected_answer()

        with open(OUTPUT_PATH, "r", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        assert reader.fieldnames == ["category", "share_pct"]
        assert len(rows) == 1, "output should contain exactly one row"

        row = rows[0]
        assert row["category"] == expected_category

        reported_share = float(row["share_pct"])
        assert abs(reported_share - expected_share) <= 0.15
        assert 0.0 < reported_share <= 100.0
