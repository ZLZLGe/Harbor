import csv
import math
import os
import unittest

import numpy as np
import pandas as pd


EXPECTED_COLUMNS = [
    "series",
    "series_code",
    "cycle_std",
    "relative_volatility_to_gdp",
]
CODE_TO_LABEL = {
    "RGDP": "GDP",
    "RPCE": "Consumption",
    "RPFI": "Fixed Investment",
}
TOLERANCE = 5e-6


def hp_cycle(values, lamb=1600.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def locate_output():
    override_dir = os.environ.get("HARBOR_OUTPUT_DIR")
    if override_dir:
        path = os.path.join(override_dir, "cycle_volatility_profile.csv")
    else:
        path = "/root/cycle_volatility_profile.csv"
    if os.path.exists(path):
        return path
    return None


def locate_input():
    candidates = [
        "/root/us_macro_quarterly_real_panel.csv",
        os.path.join(
            os.getcwd(),
            "environment",
            "us_macro_quarterly_real_panel.csv",
        ),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("us_macro_quarterly_real_panel.csv not found")


def expected_rows():
    data = pd.read_csv(locate_input())
    target = data[data["series_code"].isin(CODE_TO_LABEL)].copy()
    target = target[target["quarter"].between("1990Q1", "2024Q4")]

    rows = []
    gdp_std = None
    for code in ["RGDP", "RPCE", "RPFI"]:
        series = (
            target[target["series_code"] == code]
            .sort_values("quarter")["value"]
            .astype(float)
            .to_numpy()
        )
        cycle = hp_cycle(np.log(series), lamb=1600.0)
        cycle_std = float(np.std(cycle, ddof=1))
        if code == "RGDP":
            gdp_std = cycle_std
        rows.append(
            {
                "series": CODE_TO_LABEL[code],
                "series_code": code,
                "cycle_std": cycle_std,
            }
        )

    for row in rows:
        row["relative_volatility_to_gdp"] = row["cycle_std"] / gdp_std

    rows.sort(key=lambda item: item["relative_volatility_to_gdp"], reverse=True)
    return rows


class TestCycleVolatilityProfile(unittest.TestCase):
    def test_output_exists(self):
        self.assertIsNotNone(
            locate_output(),
            "Missing cycle_volatility_profile.csv",
        )

    def test_csv_schema_and_row_count(self):
        output = locate_output()
        if output is None:
            self.skipTest("output missing")

        with open(output, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, EXPECTED_COLUMNS)
            rows = list(reader)

        self.assertEqual(len(rows), 3)

    def test_series_order_and_values(self):
        output = locate_output()
        if output is None:
            self.skipTest("output missing")

        with open(output, newline="", encoding="utf-8") as handle:
            raw_rows = list(csv.DictReader(handle))

        actual = pd.read_csv(output)
        expected = pd.DataFrame(expected_rows())

        self.assertEqual(actual["series"].tolist(), expected["series"].tolist())
        self.assertEqual(actual["series_code"].tolist(), expected["series_code"].tolist())

        relative_values = actual["relative_volatility_to_gdp"].astype(float).tolist()
        self.assertEqual(relative_values, sorted(relative_values, reverse=True))

        for actual_row in raw_rows:
            cycle_text = actual_row["cycle_std"]
            ratio_text = actual_row["relative_volatility_to_gdp"]
            self.assertRegex(cycle_text, r"^-?\d+\.\d{6}$")
            self.assertRegex(ratio_text, r"^-?\d+\.\d{6}$")

        for index in range(len(expected)):
            self.assertTrue(
                math.isclose(
                    float(actual.loc[index, "cycle_std"]),
                    expected.loc[index, "cycle_std"],
                    abs_tol=TOLERANCE,
                )
            )
            self.assertTrue(
                math.isclose(
                    float(actual.loc[index, "relative_volatility_to_gdp"]),
                    expected.loc[index, "relative_volatility_to_gdp"],
                    abs_tol=TOLERANCE,
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
