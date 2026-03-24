import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RESULT_PATH = Path("/root/boulder_best_config.json")
DATA_DIR = Path("/root/data")
REQUIRED_KEYS = {
    "min_samples",
    "epsilon",
    "direction_weight",
    "validation_f1",
    "validation_mean_centroid_error",
}


def pairwise_euclidean(points_a, points_b=None):
    if points_b is None:
        points_b = points_a
    diff = points_a[:, np.newaxis, :] - points_b[np.newaxis, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def greedy_match(centroids, experts, max_distance=60.0):
    if len(centroids) == 0 or len(experts) == 0:
        return 0, len(centroids), len(experts), []

    distances = pairwise_euclidean(centroids, experts)
    matches = []
    while True:
        row_idx, col_idx = np.unravel_index(np.argmin(distances), distances.shape)
        best_distance = distances[row_idx, col_idx]
        if not np.isfinite(best_distance) or best_distance > max_distance:
            break
        matches.append((row_idx, col_idx, float(best_distance)))
        distances[row_idx, :] = np.inf
        distances[:, col_idx] = np.inf

    true_positive = len(matches)
    false_positive = len(centroids) - true_positive
    false_negative = len(experts) - true_positive
    return true_positive, false_positive, false_negative, matches


def compute_distance_matrix(rotated_points, direction_weight):
    coeffs = np.array([2.0 - direction_weight, direction_weight])
    diff = rotated_points[:, np.newaxis, :] - rotated_points[np.newaxis, :, :]
    weighted = diff * coeffs
    return np.sqrt((weighted**2).sum(axis=2))


def dbscan_precomputed(dist_matrix, epsilon, min_samples):
    point_count = len(dist_matrix)
    labels = np.full(point_count, -99, dtype=int)
    neighbors = [np.where(dist_matrix[idx] <= epsilon)[0] for idx in range(point_count)]
    is_core = [len(items) >= min_samples for items in neighbors]
    cluster_id = 0

    for idx in range(point_count):
        if labels[idx] != -99:
            continue
        if not is_core[idx]:
            labels[idx] = -1
            continue

        labels[idx] = cluster_id
        seeds = list(neighbors[idx][neighbors[idx] != idx])
        seen = set(seeds)
        cursor = 0
        while cursor < len(seeds):
            neighbor_idx = seeds[cursor]
            if labels[neighbor_idx] == -1:
                labels[neighbor_idx] = cluster_id
            if labels[neighbor_idx] != -99:
                cursor += 1
                continue

            labels[neighbor_idx] = cluster_id
            if is_core[neighbor_idx]:
                for candidate_idx in neighbors[neighbor_idx]:
                    if candidate_idx not in seen:
                        seeds.append(candidate_idx)
                        seen.add(candidate_idx)
            cursor += 1

        cluster_id += 1

    labels[labels == -99] = -1
    return labels


def build_tile_data():
    clicks_df = pd.read_csv(DATA_DIR / "boulder_clicks_validation.csv")
    experts_df = pd.read_csv(DATA_DIR / "boulder_expert_validation.csv")
    meta_df = pd.read_csv(DATA_DIR / "tile_metadata.csv")
    angles_deg = dict(zip(meta_df["tile_id"], meta_df["track_angle_deg"]))

    tile_data = []
    for tile_id in experts_df["tile_id"].drop_duplicates():
        clicks = clicks_df.loc[clicks_df["tile_id"] == tile_id, ["x", "y"]].to_numpy(dtype=float)
        experts = experts_df.loc[experts_df["tile_id"] == tile_id, ["x", "y"]].to_numpy(dtype=float)
        theta = np.deg2rad(angles_deg[tile_id])
        rotation = np.array(
            [
                [np.cos(theta), -np.sin(theta)],
                [np.sin(theta), np.cos(theta)],
            ]
        )
        tile_data.append(
            {
                "tile_id": tile_id,
                "clicks": clicks,
                "experts": experts,
                "rotated_clicks": clicks @ rotation,
            }
        )
    return tile_data


def evaluate_config(config, tile_data):
    min_samples, epsilon, direction_weight = config
    f1_scores = []
    centroid_errors = []

    for tile in tile_data:
        clicks = tile["clicks"]
        experts = tile["experts"]
        if len(clicks) == 0:
            f1_scores.append(0.0)
            continue

        dist_matrix = compute_distance_matrix(tile["rotated_clicks"], direction_weight)
        labels = dbscan_precomputed(dist_matrix, epsilon, min_samples)
        cluster_ids = [cluster_id for cluster_id in sorted(set(labels)) if cluster_id != -1]
        if not cluster_ids:
            f1_scores.append(0.0)
            continue

        centroids = np.array([clicks[labels == cluster_id].mean(axis=0) for cluster_id in cluster_ids])
        tp, fp, fn, matches = greedy_match(centroids, experts)
        if tp == 0:
            f1_scores.append(0.0)
            continue

        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        f1_scores.append(2.0 * precision * recall / (precision + recall))
        centroid_errors.append(float(np.mean([match[2] for match in matches])))

    mean_f1 = float(np.mean(f1_scores))
    mean_error = float(np.mean(centroid_errors)) if centroid_errors else float("inf")
    return mean_f1, mean_error


def compute_expected_result():
    tile_data = build_tile_data()
    best_result = None
    best_key = None

    for config in product(
        [3, 4, 5, 6],
        [10, 12, 14, 16, 18, 20, 22],
        [1.0, 1.2, 1.4, 1.6, 1.8],
    ):
        mean_f1, mean_error = evaluate_config(config, tile_data)
        min_samples, epsilon, direction_weight = config
        rank_key = (-mean_f1, mean_error, epsilon, min_samples, direction_weight)
        if best_key is None or rank_key < best_key:
            best_key = rank_key
            best_result = {
                "min_samples": min_samples,
                "epsilon": epsilon,
                "direction_weight": round(direction_weight, 1),
                "validation_f1": round(mean_f1, 5),
                "validation_mean_centroid_error": round(mean_error, 5),
            }

    return best_result


@pytest.fixture(scope="module")
def result_data():
    assert RESULT_PATH.exists(), f"Result file not found: {RESULT_PATH}"
    return json.loads(RESULT_PATH.read_text())


@pytest.fixture(scope="module")
def expected_result():
    return compute_expected_result()


def test_result_file_exists():
    assert RESULT_PATH.exists(), f"Result file not found: {RESULT_PATH}"


def test_result_is_valid_json_object(result_data):
    assert isinstance(result_data, dict), "Output must be a JSON object"
    missing = REQUIRED_KEYS - set(result_data)
    assert not missing, f"Missing keys: {sorted(missing)}"


def test_result_values_are_in_search_space(result_data):
    assert int(result_data["min_samples"]) in {3, 4, 5, 6}
    assert int(result_data["epsilon"]) in {10, 12, 14, 16, 18, 20, 22}
    assert round(float(result_data["direction_weight"]), 1) in {1.0, 1.2, 1.4, 1.6, 1.8}
    assert 0.0 <= float(result_data["validation_f1"]) <= 1.0
    assert float(result_data["validation_mean_centroid_error"]) > 0.0


def test_result_matches_expected_best_config(result_data, expected_result):
    assert int(result_data["min_samples"]) == expected_result["min_samples"]
    assert int(result_data["epsilon"]) == expected_result["epsilon"]
    assert round(float(result_data["direction_weight"]), 1) == expected_result["direction_weight"]
    assert abs(float(result_data["validation_f1"]) - expected_result["validation_f1"]) <= 1e-5
    assert (
        abs(
            float(result_data["validation_mean_centroid_error"])
            - expected_result["validation_mean_centroid_error"]
        )
        <= 1e-5
    )
