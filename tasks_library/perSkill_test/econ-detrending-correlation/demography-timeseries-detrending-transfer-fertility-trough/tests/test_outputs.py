import unittest
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_NAME = "fertility-cycle-trough.csv"
DATA_NAME = "fertility_inputs.csv"
ANNUAL_LAMBDA = 100


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


def expected_metrics() -> dict[str, float | int]:
    df = pd.read_csv(resolve_data_path()).sort_values("year").reset_index(drop=True)
    df["general_fertility_rate"] = df["births"] / df["women_15_44"] * 1000.0

    annual_cycle = hp_cycle(df["general_fertility_rate"], ANNUAL_LAMBDA)
    logged_cycle = hp_cycle(np.log(df["general_fertility_rate"]), ANNUAL_LAMBDA)
    wrong_lambda_cycle = hp_cycle(df["general_fertility_rate"], 1600)

    trough_idx = int(np.argmin(annual_cycle))
    raw_idx = int(df["general_fertility_rate"].idxmin())
    wrong_lambda_idx = int(np.argmin(wrong_lambda_cycle))

    return {
        "year": int(df.loc[trough_idx, "year"]),
        "cycle_gap": round(float(annual_cycle[trough_idx]), 5),
        "logged_cycle_gap": float(logged_cycle[trough_idx]),
        "raw_min_year": int(df.loc[raw_idx, "year"]),
        "wrong_lambda_year": int(df.loc[wrong_lambda_idx, "year"]),
        "wrong_lambda_gap": float(wrong_lambda_cycle[wrong_lambda_idx]),
    }


class FertilityCycleTroughTests(unittest.TestCase):
    def test_output_file_exists(self) -> None:
        self.assertIsNotNone(
            resolve_output_path(),
            f"Expected /root/{OUTPUT_NAME} to exist",
        )

    def test_output_schema(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        df = pd.read_csv(output_path)
        self.assertEqual(list(df.columns), ["year", "cycle_gap"])
        self.assertEqual(len(df), 1, "Output must contain exactly one row")

    def test_output_matches_expected_trough(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        actual = pd.read_csv(output_path)
        expected = expected_metrics()

        self.assertEqual(int(actual.loc[0, "year"]), expected["year"])
        self.assertAlmostEqual(
            float(actual.loc[0, "cycle_gap"]),
            expected["cycle_gap"],
            places=5,
        )

    def test_output_reflects_detrended_rate_not_raw_minimum(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        actual = pd.read_csv(output_path)
        expected = expected_metrics()

        self.assertNotEqual(
            int(actual.loc[0, "year"]),
            expected["raw_min_year"],
            "Answer should not just use the year with the lowest observed fertility rate",
        )
        self.assertNotEqual(
            int(actual.loc[0, "year"]),
            expected["wrong_lambda_year"],
            "Answer matches lambda=1600 rather than the annual HP specification",
        )
        self.assertGreater(
            abs(float(actual.loc[0, "cycle_gap"]) - expected["logged_cycle_gap"]),
            0.5,
            "Answer is too close to applying the HP filter to logged rates instead of level rates",
        )
        self.assertGreater(
            abs(float(actual.loc[0, "cycle_gap"]) - expected["wrong_lambda_gap"]),
            0.5,
            "Answer is too close to the lambda=1600 cyclical gap",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
