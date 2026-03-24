import csv
import os

import numpy as np
import pandas as pd


DATA_DIR = "/root/data"
OUTPUT_PATH = "/root/output/delinquency_pressure_share.csv"

CATEGORY_COLUMNS = {
    "Debt Load": [
        "debt_to_income_ratio",
        "credit_utilization_pct",
        "installment_balance_growth_pct",
    ],
    "Income Volatility": [
        "income_variability_pct",
        "hours_worked_cv_pct",
        "recent_job_change_pct",
    ],
    "Repayment Friction": [
        "minimum_payment_share_pct",
        "days_since_autopay_fail",
        "roll_rate_30_to_59_pct",
    ],
    "Cost Pressure": [
        "rent_to_income_pct",
        "utility_cost_index",
        "essentials_inflation_pct",
    ],
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
    borrower = pd.read_csv(f"{DATA_DIR}/borrower_profile.csv")
    payment = pd.read_csv(f"{DATA_DIR}/payment_behavior.csv")
    costs = pd.read_csv(f"{DATA_DIR}/regional_cost_panel.csv")
    targets = pd.read_csv(f"{DATA_DIR}/delinquency_targets.csv")

    df = (
        borrower.merge(payment, on="portfolio_id")
        .merge(costs, on="portfolio_id")
        .merge(targets, on="portfolio_id")
    )

    driver_columns = [column for columns in CATEGORY_COLUMNS.values() for column in columns]
    X = standardize(df[driver_columns].to_numpy(dtype=float))
    y = df["delinquency_rate_pct"].to_numpy(dtype=float)

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
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    fitted = design @ beta
    full_mse = np.mean((y - fitted) ** 2)

    raw_contributions = {}
    for category in CATEGORY_COLUMNS:
        factor_ids = [
            idx for idx, mapped_category in factor_to_category.items()
            if mapped_category == category
        ]
        if not factor_ids:
            raw_contributions[category] = 0.0
            continue
        beta_leave = beta.copy()
        for factor_idx in factor_ids:
            beta_leave[factor_idx + 1] = 0.0
        fitted_leave = design @ beta_leave
        raw_contributions[category] = max(
            np.mean((y - fitted_leave) ** 2) - full_mse,
            0.0,
        )

    total = sum(raw_contributions.values())
    share_pct = {
        category: 100.0 * value / total
        for category, value in raw_contributions.items()
    }
    dominant_category = max(share_pct, key=share_pct.get)
    return dominant_category, share_pct[dominant_category]


class TestCreditDelinquencyPressureShare:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), "delinquency_pressure_share.csv not found"

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
