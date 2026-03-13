#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/tests")
sys.path.insert(0, "/tests/src")

from evaluate import evaluate_solution


OUTPUT_PATH = Path("/output/coastal_corridor_plan.json")
SCENARIO_PATH = Path("/data/coastal_corridor/scenario.json")
GROUND_TRUTH_PATH = Path("/tests/ground_truths/coastal_corridor/ground_truth.json")
SCORE_PATH = Path("/logs/verifier/scores/coastal_corridor.txt")
EXPECTED_DISTRICTS = [
    "HARBOR",
    "COMMERCIAL_HUB",
    "CANAL",
    "AQUEDUCT",
    "INDUSTRIAL_ZONE",
]


@pytest.fixture(scope="session", autouse=True)
def setup_score_dir():
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def solution():
    if not OUTPUT_PATH.exists():
        pytest.fail(f"Solution file not found: {OUTPUT_PATH}")
    with OUTPUT_PATH.open() as f:
        return json.load(f)


def test_solution_file_exists():
    assert OUTPUT_PATH.exists(), f"Solution file not found: {OUTPUT_PATH}"


def test_solution_is_valid_json():
    with OUTPUT_PATH.open() as f:
        data = json.load(f)
    assert isinstance(data, dict), "Solution must be a JSON object"


def test_has_required_fields(solution):
    assert "city_center" in solution, "Solution missing 'city_center'"
    assert isinstance(solution["city_center"], list) and len(solution["city_center"]) == 2, \
        "'city_center' must be [x, y]"
    assert "placements" in solution and isinstance(solution["placements"], dict), \
        "Solution missing dict field 'placements'"
    assert "adjacency_bonuses" in solution and isinstance(solution["adjacency_bonuses"], dict), \
        "Solution missing dict field 'adjacency_bonuses'"
    assert "adjacency_breakdowns" in solution and isinstance(solution["adjacency_breakdowns"], dict), \
        "Solution missing dict field 'adjacency_breakdowns'"
    assert "total_adjacency" in solution and isinstance(solution["total_adjacency"], (int, float)), \
        "Solution missing numeric field 'total_adjacency'"
    assert "weighted_score" in solution and isinstance(solution["weighted_score"], (int, float)), \
        "Solution missing numeric field 'weighted_score'"


def test_placement_keys_match_expected(solution):
    assert set(solution["placements"].keys()) == set(EXPECTED_DISTRICTS), \
        f"placements keys must be exactly {EXPECTED_DISTRICTS}"


def test_bonus_and_breakdown_keys_match_expected(solution):
    assert set(solution["adjacency_bonuses"].keys()) == set(EXPECTED_DISTRICTS), \
        f"adjacency_bonuses keys must be exactly {EXPECTED_DISTRICTS}"
    assert set(solution["adjacency_breakdowns"].keys()) == set(EXPECTED_DISTRICTS), \
        f"adjacency_breakdowns keys must be exactly {EXPECTED_DISTRICTS}"


def test_placements_have_coordinates(solution):
    for district, coords in solution["placements"].items():
        assert isinstance(coords, list), f"{district} coords must be a list"
        assert len(coords) == 2, f"{district} must have exactly 2 coordinates"
        assert all(isinstance(c, (int, float)) for c in coords), \
            f"{district} coords must be numeric"


def test_evaluate_solution():
    with OUTPUT_PATH.open() as f:
        solution = json.load(f)
    with SCENARIO_PATH.open() as f:
        scenario = json.load(f)
    with GROUND_TRUTH_PATH.open() as f:
        ground_truth = json.load(f)

    result = evaluate_solution(
        scenario=scenario,
        solution=solution,
        ground_truth=ground_truth,
        data_dir=SCENARIO_PATH.parent.parent,
    )

    score = result.score if result.valid else 0.0
    SCORE_PATH.write_text(str(score))

    assert result.valid, f"Invalid solution: {result.errors}"
    assert not result.adjacency_mismatch, f"Adjacency mismatch: {result.errors}"
