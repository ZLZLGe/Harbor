import re
import unittest
import os
from pathlib import Path

import numpy as np
import pandas as pd


TEST_DIR = Path(__file__).resolve().parent
TASK_DIR = TEST_DIR.parent
VALID_REGIONS = {"North", "South", "West", "Metro"}


def hp_cycle(values, lamb=14400.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def locate_input():
    candidates = [
        Path("/root/regional_grid_load_panel.tsv"),
        TASK_DIR / "environment" / "regional_grid_load_panel.tsv",
        Path.cwd() / "environment" / "regional_grid_load_panel.tsv",
    ]
    for path in candidates:
        try:
            exists = path.exists()
        except PermissionError:
            exists = False
        if exists:
            return path
    raise FileNotFoundError("regional_grid_load_panel.tsv not found")


def locate_output():
    env_path = os.environ.get("GRID_TROUGH_PATH")
    candidates = [Path("/root/grid_trough.txt")]
    if env_path:
        candidates.append(Path(env_path))

    for path in candidates:
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    return None


def expected_result():
    data = pd.read_csv(locate_input(), sep="\t")
    records = []
    for region, frame in data.groupby("region", sort=False):
        ordered = frame.sort_values("month").copy()
        ordered["cycle"] = hp_cycle(np.log(ordered["load_gwh"].astype(float).to_numpy()))
        records.append(ordered[["region", "month", "cycle"]])

    result = pd.concat(records, ignore_index=True)
    trough = result.loc[result["cycle"].idxmin()]
    return {
        "region": str(trough["region"]),
        "month": str(trough["month"]),
    }


def parse_output():
    output = locate_output()
    if output is None:
        raise FileNotFoundError("grid_trough.txt not found")

    text = output.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) == 2, "grid_trough.txt must contain exactly 2 lines"
    assert re.fullmatch(r"region=[A-Za-z]+", lines[0]), "Line 1 must match region=<地区名>"
    assert re.fullmatch(r"month=\d{4}-\d{2}", lines[1]), "Line 2 must match month=<YYYY-MM>"

    region = lines[0].split("=", 1)[1]
    month = lines[1].split("=", 1)[1]
    return {"region": region, "month": month}


class TestGridTrough(unittest.TestCase):
    def test_output_exists(self):
        self.assertIsNotNone(locate_output(), "Missing grid_trough.txt")

    def test_output_format_and_domain(self):
        parsed = parse_output()
        self.assertIn(parsed["region"], VALID_REGIONS)
        self.assertRegex(parsed["month"], r"^\d{4}-\d{2}$")

    def test_trough_answer_matches_expected(self):
        self.assertEqual(parse_output(), expected_result())


if __name__ == "__main__":
    unittest.main(verbosity=2)
