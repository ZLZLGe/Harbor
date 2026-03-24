import unittest
import os
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(os.environ.get("HARBOR_ROOT", "/root"))
RESULT_PATH = ROOT_DIR / "lunar_boulder_leaderboard.csv"
DATA_DIR = ROOT_DIR / "data"


def dbscan_labels(points, eps_px, min_samples):
    point_count = len(points)
    labels = np.full(point_count, -99, dtype=int)
    if point_count == 0:
        return labels

    diffs = points[:, np.newaxis, :] - points[np.newaxis, :, :]
    distances = np.sqrt((diffs * diffs).sum(axis=2))
    neighbors = [np.where(distances[idx] <= eps_px)[0] for idx in range(point_count)]

    cluster_id = 0
    for idx in range(point_count):
        if labels[idx] != -99:
            continue
        if len(neighbors[idx]) < min_samples:
            labels[idx] = -1
            continue

        labels[idx] = cluster_id
        seeds = [int(value) for value in neighbors[idx]]
        seed_set = set(seeds)
        cursor = 0
        while cursor < len(seeds):
            neighbor_idx = seeds[cursor]
            if labels[neighbor_idx] == -1:
                labels[neighbor_idx] = cluster_id
            if labels[neighbor_idx] != -99:
                cursor += 1
                continue

            labels[neighbor_idx] = cluster_id
            if len(neighbors[neighbor_idx]) >= min_samples:
                for value in neighbors[neighbor_idx]:
                    value = int(value)
                    if value not in seed_set:
                        seeds.append(value)
                        seed_set.add(value)
            cursor += 1

        cluster_id += 1

    return labels


def greedy_match(centroids, references, max_distance_px=45.0):
    if len(centroids) == 0 or len(references) == 0:
        return 0, len(centroids), len(references), []

    distances = np.sqrt(((centroids[:, np.newaxis, :] - references[np.newaxis, :, :]) ** 2).sum(axis=2))
    matches = []
    while distances.size:
        match_idx = np.unravel_index(np.argmin(distances), distances.shape)
        match_distance = float(distances[match_idx])
        if not np.isfinite(match_distance) or match_distance > max_distance_px:
            break
        matches.append(match_distance)
        distances[match_idx[0], :] = np.inf
        distances[:, match_idx[1]] = np.inf

    true_positives = len(matches)
    false_positives = len(centroids) - true_positives
    false_negatives = len(references) - true_positives
    return true_positives, false_positives, false_negatives, matches


def compute_expected_leaderboard():
    volunteer = pd.read_csv(DATA_DIR / "volunteer_boulders.csv")
    reference = pd.read_csv(DATA_DIR / "reference_boulders.csv")
    manifest = pd.read_csv(DATA_DIR / "tile_manifest.csv")

    image_data = []
    for tile_id in manifest["tile_id"]:
        volunteer_points = volunteer.loc[volunteer["tile_id"] == tile_id, ["x_px", "y_px"]].to_numpy(float)
        reference_points = reference.loc[reference["tile_id"] == tile_id, ["x_px", "y_px"]].to_numpy(float)
        image_data.append((volunteer_points, reference_points))

    rows = []
    for eps_px, min_samples, east_west_scale in product(
        [6, 8, 10, 12, 14, 16, 18],
        [2, 3, 4, 5, 6],
        [0.70, 0.85, 1.00, 1.15, 1.30, 1.45, 1.60],
    ):
        f1_scores = []
        localization_errors = []
        for volunteer_points, reference_points in image_data:
            if len(volunteer_points) == 0:
                f1_scores.append(0.0)
                continue

            scaled_points = volunteer_points * np.array([east_west_scale, 1.0])
            labels = dbscan_labels(scaled_points, eps_px, min_samples)
            cluster_labels = sorted(set(labels) - {-1, -99})
            if not cluster_labels:
                f1_scores.append(0.0)
                continue

            centroids = np.array([volunteer_points[labels == label].mean(axis=0) for label in cluster_labels])
            tp, fp, fn, matches = greedy_match(centroids, reference_points)
            if tp == 0:
                f1_scores.append(0.0)
                continue

            precision = tp / (tp + fp)
            recall = tp / (tp + fn)
            f1_scores.append(2 * precision * recall / (precision + recall))
            localization_errors.append(float(np.mean(matches)))

        rows.append(
            {
                "mean_f1": round(float(np.mean(f1_scores)), 6),
                "mean_localization_error": round(float(np.mean(localization_errors)), 6),
                "eps_px": eps_px,
                "min_samples": min_samples,
                "east_west_scale": round(east_west_scale, 2),
            }
        )

    leaderboard = pd.DataFrame(rows).sort_values(
        ["mean_f1", "mean_localization_error", "eps_px", "min_samples", "east_west_scale"],
        ascending=[False, True, True, True, True],
    ).head(15).reset_index(drop=True)
    leaderboard.insert(0, "rank", np.arange(1, len(leaderboard) + 1))
    return leaderboard


class LunarBoulderLeaderboardTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RESULT_PATH.exists(), f"missing result file: {RESULT_PATH}")
        self.result = pd.read_csv(RESULT_PATH)
        self.expected = compute_expected_leaderboard()

    def test_columns(self):
        self.assertEqual(
            list(self.result.columns),
            ["rank", "mean_f1", "mean_localization_error", "eps_px", "min_samples", "east_west_scale"],
        )

    def test_length_and_rank(self):
        self.assertEqual(len(self.result), 15)
        self.assertEqual(self.result["rank"].tolist(), list(range(1, 16)))

    def test_value_ranges(self):
        self.assertTrue(((self.result["mean_f1"] >= 0.0) & (self.result["mean_f1"] <= 1.0)).all())
        self.assertTrue((self.result["mean_localization_error"] > 0.0).all())
        self.assertTrue(self.result["eps_px"].isin([6, 8, 10, 12, 14, 16, 18]).all())
        self.assertTrue(self.result["min_samples"].isin([2, 3, 4, 5, 6]).all())
        self.assertTrue(self.result["east_west_scale"].isin([0.70, 0.85, 1.00, 1.15, 1.30, 1.45, 1.60]).all())

    def test_sorted(self):
        sorted_result = self.result.sort_values(
            ["mean_f1", "mean_localization_error", "eps_px", "min_samples", "east_west_scale"],
            ascending=[False, True, True, True, True],
        ).reset_index(drop=True)
        pd.testing.assert_frame_equal(self.result.reset_index(drop=True), sorted_result)

    def test_matches_expected_leaderboard(self):
        pd.testing.assert_frame_equal(
            self.result.reset_index(drop=True),
            self.expected.reset_index(drop=True),
            check_dtype=False,
            atol=1e-6,
            rtol=0,
        )


if __name__ == "__main__":
    unittest.main()
