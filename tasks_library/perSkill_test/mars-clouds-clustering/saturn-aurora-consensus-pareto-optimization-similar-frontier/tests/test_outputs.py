from collections import defaultdict
from itertools import product
from pathlib import Path
import os

import numpy as np
import pandas as pd
import pytest


DATA_DIR = Path(os.environ.get("AURORA_DATA_DIR", "/root/data"))
RESULT_PATH = Path(os.environ.get("AURORA_FRONTIER_PATH", "/root/aurora_frontier.csv"))

EXPECTED_COLUMNS = [
    "agreement_score",
    "localization_error",
    "min_support",
    "merge_radius",
    "latitude_scale",
]


def connected_components(points, merge_radius, latitude_scale):
    if len(points) == 0:
        return []

    parent = list(range(len(points)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dx = points[i, 0] - points[j, 0]
            dy = points[i, 1] - points[j, 1]
            distance = float(np.sqrt((dx * dx) + ((latitude_scale * dy) ** 2)))
            if distance <= merge_radius:
                union(i, j)

    groups = defaultdict(list)
    for index in range(len(points)):
        groups[find(index)].append(index)
    return list(groups.values())


def consensus_locations(points, min_support, merge_radius, latitude_scale):
    locations = []
    for component in connected_components(points, merge_radius, latitude_scale):
        if len(component) < min_support:
            continue
        component_points = points[component]
        locations.append(tuple(np.median(component_points, axis=0)))
    return locations


def greedy_matches(consensus_points, expert_points, max_distance=24):
    if len(consensus_points) == 0 or len(expert_points) == 0:
        return 0, len(consensus_points), len(expert_points), []

    candidate_pairs = []
    for consensus_index, consensus_point in enumerate(consensus_points):
        for expert_index, expert_point in enumerate(expert_points):
            distance = float(np.linalg.norm(np.array(consensus_point) - np.array(expert_point)))
            if distance <= max_distance:
                candidate_pairs.append((distance, consensus_index, expert_index))

    candidate_pairs.sort()
    used_consensus = set()
    used_experts = set()
    match_distances = []

    for distance, consensus_index, expert_index in candidate_pairs:
        if consensus_index in used_consensus or expert_index in used_experts:
            continue
        used_consensus.add(consensus_index)
        used_experts.add(expert_index)
        match_distances.append(distance)

    true_positive = len(match_distances)
    false_positive = len(consensus_points) - true_positive
    false_negative = len(expert_points) - true_positive
    return true_positive, false_positive, false_negative, match_distances


def f1_score(true_positive, false_positive, false_negative):
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def compute_expected_frontier():
    citizen_df = pd.read_csv(DATA_DIR / "citizen_aurora_marks.csv")
    expert_df = pd.read_csv(DATA_DIR / "expert_aurora_catalog.csv")
    expert_image_ids = sorted(expert_df["image_id"].unique())

    rows = []
    for min_support, merge_radius, latitude_scale in product(
        [2, 3, 4, 5],
        [8, 12, 16, 20, 24],
        [0.8, 1.0, 1.2, 1.4],
    ):
        image_scores = []
        image_errors = []

        for image_id in expert_image_ids:
            citizen_points = citizen_df.loc[citizen_df["image_id"] == image_id, ["x_px", "y_px"]].to_numpy(dtype=float)
            expert_points = expert_df.loc[expert_df["image_id"] == image_id, ["x_px", "y_px"]].to_numpy(dtype=float)

            consensus_points = consensus_locations(citizen_points, min_support, merge_radius, latitude_scale)
            true_positive, false_positive, false_negative, match_distances = greedy_matches(consensus_points, expert_points)

            image_scores.append(f1_score(true_positive, false_positive, false_negative))
            if match_distances:
                image_errors.append(float(np.mean(match_distances)))

        agreement_score = float(np.mean(image_scores))
        localization_error = float(np.mean(image_errors)) if image_errors else np.inf

        if agreement_score >= 0.50 and np.isfinite(localization_error):
            rows.append(
                {
                    "agreement_score": round(agreement_score, 5),
                    "localization_error": round(localization_error, 5),
                    "min_support": int(min_support),
                    "merge_radius": int(merge_radius),
                    "latitude_scale": round(float(latitude_scale), 1),
                }
            )

    dataframe = pd.DataFrame(rows).sort_values(
        ["agreement_score", "localization_error", "min_support", "merge_radius", "latitude_scale"],
        ascending=[False, True, True, True, True],
    )
    dataframe = dataframe.drop_duplicates(["agreement_score", "localization_error"], keep="first").reset_index(drop=True)

    keep_mask = []
    values = dataframe[["agreement_score", "localization_error"]].to_numpy()
    for index, point in enumerate(values):
        dominated = False
        for other_index, other in enumerate(values):
            if index == other_index:
                continue
            if other[0] >= point[0] and other[1] <= point[1] and (other[0] > point[0] or other[1] < point[1]):
                dominated = True
                break
        keep_mask.append(not dominated)

    return dataframe.loc[keep_mask].sort_values(
        ["agreement_score", "localization_error", "min_support", "merge_radius", "latitude_scale"],
        ascending=[False, True, True, True, True],
    ).reset_index(drop=True)


@pytest.fixture(scope="module")
def agent_output():
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"
    return pd.read_csv(RESULT_PATH)


@pytest.fixture(scope="module")
def expected_frontier():
    return compute_expected_frontier()


def test_result_exists():
    assert RESULT_PATH.exists(), f"Missing result file: {RESULT_PATH}"


def test_columns(agent_output):
    assert list(agent_output.columns) == EXPECTED_COLUMNS


def test_rows_not_empty(agent_output):
    assert len(agent_output) > 0


def test_rows_sorted(agent_output):
    sorted_output = agent_output.sort_values(
        ["agreement_score", "localization_error", "min_support", "merge_radius", "latitude_scale"],
        ascending=[False, True, True, True, True],
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(agent_output.reset_index(drop=True), sorted_output)


def test_ranges_and_filter(agent_output):
    assert agent_output["agreement_score"].between(0.50, 1.0).all()
    assert (agent_output["localization_error"] > 0).all()
    assert agent_output["min_support"].isin([2, 3, 4, 5]).all()
    assert agent_output["merge_radius"].isin([8, 12, 16, 20, 24]).all()
    assert agent_output["latitude_scale"].isin([0.8, 1.0, 1.2, 1.4]).all()


def test_no_duplicate_objective_pairs(agent_output):
    duplicates = agent_output.duplicated(subset=["agreement_score", "localization_error"]).sum()
    assert duplicates == 0


def test_frontier_is_not_dominated(agent_output):
    values = agent_output[["agreement_score", "localization_error"]].to_numpy()
    for index, point in enumerate(values):
        for other_index, other in enumerate(values):
            if index == other_index:
                continue
            assert not (
                other[0] >= point[0]
                and other[1] <= point[1]
                and (other[0] > point[0] or other[1] < point[1])
            ), f"Row {index} is dominated by row {other_index}"


def test_matches_expected_frontier(agent_output, expected_frontier):
    rounded_agent = agent_output.copy()
    rounded_expected = expected_frontier.copy()
    rounded_agent["agreement_score"] = rounded_agent["agreement_score"].round(5)
    rounded_agent["localization_error"] = rounded_agent["localization_error"].round(5)
    rounded_expected["agreement_score"] = rounded_expected["agreement_score"].round(5)
    rounded_expected["localization_error"] = rounded_expected["localization_error"].round(5)
    pd.testing.assert_frame_equal(rounded_agent.reset_index(drop=True), rounded_expected.reset_index(drop=True))
