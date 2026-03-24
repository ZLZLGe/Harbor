import csv
import os

import numpy as np
import pandas as pd


DATA_DIR = "/root/data"
OUTPUT_PATH = "/root/output/ed_bottleneck_share.csv"

DRIVER_COLUMNS = [
    "arrivals_per_hour",
    "ambulance_share_pct",
    "triage_queue_min",
    "boarded_patients",
    "bed_clean_turnaround_min",
    "admit_to_bed_min",
    "lab_tat_min",
    "ct_tat_min",
    "consult_callback_min",
    "md_hours_per_100_visits",
    "rn_hours_per_100_visits",
    "overflow_bay_open_pct",
]

CATEGORY_COLUMNS = {
    "Arrival Pressure": ["arrivals_per_hour", "ambulance_share_pct", "triage_queue_min"],
    "Bed Flow": ["boarded_patients", "bed_clean_turnaround_min", "admit_to_bed_min"],
    "Diagnostics": ["lab_tat_min", "ct_tat_min", "consult_callback_min"],
    "Staffing": ["md_hours_per_100_visits", "rn_hours_per_100_visits", "overflow_bay_open_pct"],
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
    metrics = pd.read_csv(f"{DATA_DIR}/ed_operational_metrics.csv")
    targets = pd.read_csv(f"{DATA_DIR}/ed_wait_targets.csv")
    df = metrics.merge(targets, on="day_id")

    X = standardize(df[DRIVER_COLUMNS].to_numpy(dtype=float))
    y = df["p90_wait_minutes"].to_numpy(dtype=float)

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
                    [column_index[column] for column in CATEGORY_COLUMNS[category]],
                    factor_idx,
                ]
            ).mean(),
        )

    design = np.column_stack([np.ones(len(df)), scores])
    beta = np.linalg.lstsq(design, y, rcond=None)[0][1:]

    raw_contributions = {category: 0.0 for category in CATEGORY_COLUMNS}
    for category in CATEGORY_COLUMNS:
        factor_ids = [
            idx for idx, mapped_category in factor_to_category.items()
            if mapped_category == category
        ]
        if factor_ids:
            signal = scores[:, factor_ids] @ beta[factor_ids]
            raw_contributions[category] = signal.var(ddof=0)

    total_contribution = sum(raw_contributions.values())
    share_pct = {
        category: 100.0 * contribution / total_contribution
        for category, contribution in raw_contributions.items()
    }

    dominant_category = max(share_pct, key=share_pct.get)
    return dominant_category, share_pct[dominant_category]


class TestEmergencyWaitBottleneckShare:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), "ed_bottleneck_share.csv not found"

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
