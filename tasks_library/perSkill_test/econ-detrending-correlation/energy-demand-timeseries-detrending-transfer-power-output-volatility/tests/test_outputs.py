import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_NAME = "power-output-cycle-volatility.json"
DATA_NAME = "us_power_output_monthly.jsonl"
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


def compute_expected_metrics() -> dict[str, float]:
    df = pd.read_json(resolve_data_path(), lines=True)

    power_cycle = hp_cycle(np.log(df["commercial_power_gwh"]), MONTHLY_LAMBDA)
    production_cycle = hp_cycle(np.log(df["industrial_production_index"]), MONTHLY_LAMBDA)

    power_std = float(np.std(power_cycle, ddof=1))
    production_std = float(np.std(production_cycle, ddof=1))
    ratio = power_std / production_std

    level_ratio = float(
        np.std(hp_cycle(df["commercial_power_gwh"], MONTHLY_LAMBDA), ddof=1)
        / np.std(hp_cycle(df["industrial_production_index"], MONTHLY_LAMBDA), ddof=1)
    )
    wrong_lambda_ratio = float(
        np.std(hp_cycle(np.log(df["commercial_power_gwh"]), 1600), ddof=1)
        / np.std(hp_cycle(np.log(df["industrial_production_index"]), 1600), ddof=1)
    )

    return {
        "commercial_power_cycle_std": round(power_std, 5),
        "industrial_production_cycle_std": round(production_std, 5),
        "power_to_output_volatility_ratio": round(ratio, 5),
        "level_ratio": level_ratio,
        "wrong_lambda_ratio": wrong_lambda_ratio,
    }


class PowerOutputCycleVolatilityTests(unittest.TestCase):
    def test_output_file_exists(self) -> None:
        self.assertIsNotNone(
            resolve_output_path(),
            f"Expected /root/{OUTPUT_NAME} to exist",
        )

    def test_output_schema_and_rounding(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(
            set(payload.keys()),
            {
                "commercial_power_cycle_std",
                "industrial_production_cycle_std",
                "power_to_output_volatility_ratio",
            },
        )

        for key, value in payload.items():
            self.assertIsInstance(value, (int, float), f"{key} must be numeric")
            self.assertAlmostEqual(
                value,
                round(float(value), 5),
                places=10,
                msg=f"{key} must be rounded to 5 decimal places",
            )

    def test_output_matches_expected_metrics(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        expected = compute_expected_metrics()

        self.assertAlmostEqual(
            payload["commercial_power_cycle_std"],
            expected["commercial_power_cycle_std"],
            places=5,
        )
        self.assertAlmostEqual(
            payload["industrial_production_cycle_std"],
            expected["industrial_production_cycle_std"],
            places=5,
        )
        self.assertAlmostEqual(
            payload["power_to_output_volatility_ratio"],
            expected["power_to_output_volatility_ratio"],
            places=5,
        )

    def test_ratio_consistency_and_method_choice(self) -> None:
        output_path = resolve_output_path()
        self.assertIsNotNone(output_path, "Output file missing")

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        expected = compute_expected_metrics()

        implied_ratio = (
            payload["commercial_power_cycle_std"] / payload["industrial_production_cycle_std"]
        )
        self.assertAlmostEqual(
            payload["power_to_output_volatility_ratio"],
            implied_ratio,
            places=3,
            msg="Reported ratio should be consistent with the reported component volatilities",
        )
        self.assertGreater(
            abs(payload["power_to_output_volatility_ratio"] - expected["level_ratio"]),
            0.05,
            "Answer is too close to using level data instead of logged series",
        )
        self.assertGreater(
            abs(payload["power_to_output_volatility_ratio"] - expected["wrong_lambda_ratio"]),
            0.01,
            "Answer is too close to using lambda=1600 instead of the monthly parameter",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
