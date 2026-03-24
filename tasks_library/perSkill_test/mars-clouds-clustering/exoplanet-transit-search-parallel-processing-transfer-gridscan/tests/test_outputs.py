import os
import unittest
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(os.environ.get("HARBOR_ROOT", "/root"))
RESULT_PATH = ROOT_DIR / "transit_template_rankings.csv"
DATA_DIR = ROOT_DIR / "data"

PERIOD_GRID = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
DURATION_GRID = [2, 3, 4, 5]
DEPTH_GRID = [6, 8, 10, 12, 14]
EPOCH_GRID = [0, 6, 12, 18]
FALSE_ALARM_DELTA_CHI2 = 20.0


def load_star_data():
    light_curves = pd.read_csv(DATA_DIR / "light_curves.csv")
    catalog = pd.read_csv(DATA_DIR / "validation_catalog.csv")

    records = []
    for row in catalog.itertuples(index=False):
        subset = light_curves.loc[light_curves["star_id"] == row.star_id]
        time_days = subset["time_days"].to_numpy(float)
        flux = subset["flux"].to_numpy(float)
        flux_err = subset["flux_err"].to_numpy(float)
        records.append(
            {
                "is_transiting": int(row.is_transiting),
                "time_days": time_days,
                "flux": flux,
                "flux_err": flux_err,
                "flat_chi2": float(np.sum(((flux - 1.0) / flux_err) ** 2)),
                "n_obs": len(time_days),
            }
        )
    return records


def evaluate_template(params, star_data):
    period_days, duration_hours, depth_ppt, epoch_hours = params
    duration_days = duration_hours / 24.0
    depth = depth_ppt / 1000.0

    positive_scores = []
    negative_flags = []
    for record in star_data:
        phase = np.mod(record["time_days"] - epoch_hours / 24.0, period_days)
        model_flux = np.ones(record["n_obs"], dtype=float)
        model_flux[phase < duration_days] -= depth
        template_chi2 = float(np.sum(((record["flux"] - model_flux) / record["flux_err"]) ** 2))
        delta_chi2 = max(record["flat_chi2"] - template_chi2, 0.0)
        detection_score = delta_chi2 / record["n_obs"]

        if record["is_transiting"] == 1:
            positive_scores.append(detection_score)
        else:
            negative_flags.append(1 if delta_chi2 >= FALSE_ALARM_DELTA_CHI2 else 0)

    mean_detection_score = float(np.mean(positive_scores))
    false_alarm_rate = float(np.mean(negative_flags))
    composite_score = mean_detection_score - 0.75 * false_alarm_rate

    return {
        "composite_score": round(composite_score, 6),
        "mean_detection_score": round(mean_detection_score, 6),
        "false_alarm_rate": round(false_alarm_rate, 6),
        "period_days": round(period_days, 1),
        "duration_hours": duration_hours,
        "depth_ppt": depth_ppt,
        "epoch_hours": epoch_hours,
    }


def compute_expected_rankings():
    star_data = load_star_data()
    rows = [
        evaluate_template(params, star_data)
        for params in product(PERIOD_GRID, DURATION_GRID, DEPTH_GRID, EPOCH_GRID)
    ]
    rankings = pd.DataFrame(rows).sort_values(
        [
            "composite_score",
            "mean_detection_score",
            "false_alarm_rate",
            "period_days",
            "duration_hours",
            "depth_ppt",
            "epoch_hours",
        ],
        ascending=[False, False, True, True, True, True, True],
    ).head(20).reset_index(drop=True)
    rankings.insert(0, "rank", np.arange(1, len(rankings) + 1))
    return rankings


class TransitTemplateRankingTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RESULT_PATH.exists(), f"missing result file: {RESULT_PATH}")
        self.result = pd.read_csv(RESULT_PATH)
        self.expected = compute_expected_rankings()

    def test_columns(self):
        self.assertEqual(
            list(self.result.columns),
            [
                "rank",
                "composite_score",
                "mean_detection_score",
                "false_alarm_rate",
                "period_days",
                "duration_hours",
                "depth_ppt",
                "epoch_hours",
            ],
        )

    def test_length_and_rank(self):
        self.assertEqual(len(self.result), 20)
        self.assertEqual(self.result["rank"].tolist(), list(range(1, 21)))

    def test_grid_membership(self):
        self.assertTrue(self.result["period_days"].isin(PERIOD_GRID).all())
        self.assertTrue(self.result["duration_hours"].isin(DURATION_GRID).all())
        self.assertTrue(self.result["depth_ppt"].isin(DEPTH_GRID).all())
        self.assertTrue(self.result["epoch_hours"].isin(EPOCH_GRID).all())

    def test_metric_ranges(self):
        self.assertTrue((self.result["mean_detection_score"] >= 0.0).all())
        self.assertTrue((self.result["false_alarm_rate"] >= 0.0).all())
        self.assertTrue((self.result["false_alarm_rate"] <= 1.0).all())

    def test_sorted(self):
        sorted_result = self.result.sort_values(
            [
                "composite_score",
                "mean_detection_score",
                "false_alarm_rate",
                "period_days",
                "duration_hours",
                "depth_ppt",
                "epoch_hours",
            ],
            ascending=[False, False, True, True, True, True, True],
        ).reset_index(drop=True)
        pd.testing.assert_frame_equal(self.result.reset_index(drop=True), sorted_result)

    def test_matches_expected_rankings(self):
        pd.testing.assert_frame_equal(
            self.result.reset_index(drop=True),
            self.expected.reset_index(drop=True),
            check_dtype=False,
            atol=1e-6,
            rtol=0,
        )


if __name__ == "__main__":
    unittest.main()
