import unittest
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_NAME = "beveridge-cycle-corr.txt"
DATA_NAME = "us_beveridge_monthly.csv"
MONTHLY_LAMBDA = 129600


def resolve_output_path() -> Path | None:
    candidates = [
        Path("/root") / OUTPUT_NAME,
        Path.cwd() / OUTPUT_NAME,
    ]
    for path in candidates:
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    return None


def resolve_data_path() -> Path:
    candidates = [
        Path("/root") / DATA_NAME,
        Path(__file__).resolve().parents[1] / "environment" / DATA_NAME,
    ]
    for path in candidates:
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    raise FileNotFoundError(f"Could not locate {DATA_NAME}")


def hp_cycle(values: pd.Series | np.ndarray, lamb: float) -> np.ndarray:
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.zeros((n - 2, n))
    idx = np.arange(n - 2)
    second_diff[idx, idx] = 1.0
    second_diff[idx, idx + 1] = -2.0
    second_diff[idx, idx + 2] = 1.0
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def compute_correlations() -> tuple[str, float, float]:
    df = pd.read_csv(resolve_data_path())

    level_corr = float(
        np.corrcoef(
            hp_cycle(df["unemployment_rate"], MONTHLY_LAMBDA),
            hp_cycle(df["job_openings_rate"], MONTHLY_LAMBDA),
        )[0, 1]
    )
    logged_corr = float(
        np.corrcoef(
            hp_cycle(np.log(df["unemployment_rate"]), MONTHLY_LAMBDA),
            hp_cycle(np.log(df["job_openings_rate"]), MONTHLY_LAMBDA),
        )[0, 1]
    )
    wrong_lambda_corr = float(
        np.corrcoef(
            hp_cycle(df["unemployment_rate"], 1600),
            hp_cycle(df["job_openings_rate"], 1600),
        )[0, 1]
    )
    return f"{level_corr:.5f}", logged_corr, wrong_lambda_corr


class BeveridgeCycleTests(unittest.TestCase):
    def test_output_file_exists(self) -> None:
        self.assertIsNotNone(
            resolve_output_path(),
            f"Expected /root/{OUTPUT_NAME} to exist",
        )

    def test_output_format_and_value(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        content = output_path.read_text(encoding="utf-8").strip()
        self.assertRegex(
            content,
            r"^-?\d+\.\d{5}$",
            "Output must be a single decimal number rounded to 5 decimal places",
        )

        expected, _, _ = compute_correlations()
        self.assertEqual(content, expected, f"Expected {expected}, got {content}")

    def test_output_matches_level_monthly_spec(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        actual = float(output_path.read_text(encoding="utf-8").strip())
        expected, logged_corr, wrong_lambda_corr = compute_correlations()

        self.assertLess(
            abs(actual - float(expected)),
            1e-9,
            "Answer does not match the monthly HP-filtered level-rate correlation",
        )
        self.assertGreater(
            abs(actual - logged_corr),
            0.01,
            "Answer is too close to the logged-series correlation; rate series should not be log-transformed",
        )
        self.assertGreater(
            abs(actual - wrong_lambda_corr),
            0.01,
            "Answer is too close to using lambda=1600 instead of the monthly parameter",
        )

    def test_output_is_valid_correlation(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        value = float(output_path.read_text(encoding="utf-8").strip())
        self.assertGreaterEqual(value, -1.0)
        self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
