import math
from pathlib import Path

import pandas as pd
import pytest


DATA_DIR = Path("/root/data")
RESULT_PATH = Path("/root/storm_cell_links.csv")
EXPECTED_COLUMNS = [
    "case_id",
    "from_frame_time",
    "to_frame_time",
    "from_cell_id",
    "to_cell_id",
    "dx_km",
    "dy_km",
    "weighted_distance_km",
    "selected_profile",
    "max_link_distance_km",
]


def greedy_links(prev_df, next_df, east_west_weight, north_south_weight, max_link_distance_km):
    candidates = []

    for prev_row in prev_df.itertuples(index=False):
        for next_row in next_df.itertuples(index=False):
            dx = float(next_row.centroid_x_km) - float(prev_row.centroid_x_km)
            dy = float(next_row.centroid_y_km) - float(prev_row.centroid_y_km)
            distance = math.sqrt((east_west_weight * dx) ** 2 + (north_south_weight * dy) ** 2)
            candidates.append(
                {
                    "case_id": prev_row.case_id,
                    "from_frame_time": prev_row.frame_time,
                    "to_frame_time": next_row.frame_time,
                    "from_cell_id": prev_row.cell_id,
                    "to_cell_id": next_row.cell_id,
                    "dx_km": dx,
                    "dy_km": dy,
                    "weighted_distance_km": distance,
                }
            )

    candidates.sort(
        key=lambda item: (
            item["weighted_distance_km"],
            item["from_cell_id"],
            item["to_cell_id"],
        )
    )

    used_prev = set()
    used_next = set()
    selected = []

    for candidate in candidates:
        if candidate["weighted_distance_km"] > max_link_distance_km:
            break
        if candidate["from_cell_id"] in used_prev or candidate["to_cell_id"] in used_next:
            continue
        used_prev.add(candidate["from_cell_id"])
        used_next.add(candidate["to_cell_id"])
        selected.append(candidate)

    return selected


def evaluate_profile(profile_row, archive_prev_df, archive_next_df, truth_df):
    case_scores = []
    mean_correct_costs = []

    for case_id in truth_df["case_id"].drop_duplicates():
        prev_case = archive_prev_df.loc[archive_prev_df["case_id"] == case_id]
        next_case = archive_next_df.loc[archive_next_df["case_id"] == case_id]
        predicted = greedy_links(
            prev_case,
            next_case,
            float(profile_row.east_west_weight),
            float(profile_row.north_south_weight),
            float(profile_row.max_link_distance_km),
        )

        predicted_pairs = {(item["from_cell_id"], item["to_cell_id"]) for item in predicted}
        truth_pairs = {
            (row.from_cell_id, row.to_cell_id)
            for row in truth_df.loc[truth_df["case_id"] == case_id].itertuples(index=False)
        }

        true_positive = len(predicted_pairs & truth_pairs)
        false_positive = len(predicted_pairs - truth_pairs)
        false_negative = len(truth_pairs - predicted_pairs)

        if true_positive == 0:
            case_scores.append(0.0)
        else:
            case_scores.append((2.0 * true_positive) / (2.0 * true_positive + false_positive + false_negative))

        correct_costs = [
            item["weighted_distance_km"]
            for item in predicted
            if (item["from_cell_id"], item["to_cell_id"]) in truth_pairs
        ]
        if correct_costs:
            mean_correct_costs.append(sum(correct_costs) / len(correct_costs))

    validation_f1 = sum(case_scores) / len(case_scores)
    validation_mean_correct_cost = (
        sum(mean_correct_costs) / len(mean_correct_costs) if mean_correct_costs else float("inf")
    )

    return {
        "profile_id": profile_row.profile_id,
        "east_west_weight": float(profile_row.east_west_weight),
        "north_south_weight": float(profile_row.north_south_weight),
        "max_link_distance_km": float(profile_row.max_link_distance_km),
        "validation_f1": validation_f1,
        "validation_mean_correct_cost": validation_mean_correct_cost,
    }


def compute_best_profile():
    profiles_df = pd.read_csv(DATA_DIR / "link_profiles.csv")
    archive_prev_df = pd.read_csv(DATA_DIR / "archive_prev_cells.csv")
    archive_next_df = pd.read_csv(DATA_DIR / "archive_next_cells.csv")
    truth_df = pd.read_csv(DATA_DIR / "archive_manual_links.csv")

    evaluations = [
        evaluate_profile(profile_row, archive_prev_df, archive_next_df, truth_df)
        for profile_row in profiles_df.itertuples(index=False)
    ]
    evaluations.sort(
        key=lambda item: (
            -item["validation_f1"],
            item["validation_mean_correct_cost"],
            item["profile_id"],
        )
    )
    return evaluations[0]


def compute_expected_output(best_profile):
    live_prev_df = pd.read_csv(DATA_DIR / "live_prev_cells.csv")
    live_next_df = pd.read_csv(DATA_DIR / "live_next_cells.csv")

    rows = []
    for case_id in live_prev_df["case_id"].drop_duplicates():
        prev_case = live_prev_df.loc[live_prev_df["case_id"] == case_id]
        next_case = live_next_df.loc[live_next_df["case_id"] == case_id]
        predicted = greedy_links(
            prev_case,
            next_case,
            best_profile["east_west_weight"],
            best_profile["north_south_weight"],
            best_profile["max_link_distance_km"],
        )
        for item in predicted:
            rows.append(
                {
                    "case_id": item["case_id"],
                    "from_frame_time": item["from_frame_time"],
                    "to_frame_time": item["to_frame_time"],
                    "from_cell_id": item["from_cell_id"],
                    "to_cell_id": item["to_cell_id"],
                    "dx_km": round(item["dx_km"], 1),
                    "dy_km": round(item["dy_km"], 1),
                    "weighted_distance_km": round(item["weighted_distance_km"], 5),
                    "selected_profile": best_profile["profile_id"],
                    "max_link_distance_km": round(best_profile["max_link_distance_km"], 1),
                }
            )

    expected_df = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
    return expected_df.sort_values(["case_id", "from_cell_id"]).reset_index(drop=True)


@pytest.fixture(scope="module")
def result_df():
    assert RESULT_PATH.exists(), f"Result file not found: {RESULT_PATH}"
    return pd.read_csv(RESULT_PATH)


@pytest.fixture(scope="module")
def best_profile():
    return compute_best_profile()


@pytest.fixture(scope="module")
def expected_df(best_profile):
    return compute_expected_output(best_profile)


def test_result_exists():
    assert RESULT_PATH.exists(), f"Result file not found: {RESULT_PATH}"


def test_required_columns(result_df):
    assert list(result_df.columns) == EXPECTED_COLUMNS


def test_best_profile_is_unique(best_profile):
    assert best_profile["profile_id"] == "zonal_relaxed"
    assert round(best_profile["validation_f1"], 6) == 1.0


def test_selected_profile_column(result_df, best_profile):
    assert len(result_df) == 4
    assert set(result_df["selected_profile"]) == {best_profile["profile_id"]}
    assert set(result_df["max_link_distance_km"].round(1)) == {round(best_profile["max_link_distance_km"], 1)}


def test_matches_expected_output(result_df, expected_df):
    comparable = result_df.copy()
    comparable["dx_km"] = comparable["dx_km"].round(1)
    comparable["dy_km"] = comparable["dy_km"].round(1)
    comparable["weighted_distance_km"] = comparable["weighted_distance_km"].round(5)
    comparable["max_link_distance_km"] = comparable["max_link_distance_km"].round(1)

    pd.testing.assert_frame_equal(
        comparable.reset_index(drop=True),
        expected_df.reset_index(drop=True),
        check_dtype=False,
        atol=1e-6,
        rtol=0.0,
    )
