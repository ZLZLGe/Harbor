#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/tests")
sys.path.insert(0, "/tests/src")

from evaluate import evaluate_solution


OUTPUT_PATH = Path("/output/two_city_empire_plan.json")
SCENARIO_PATH = Path("/data/two_city_empire/scenario.json")
GROUND_TRUTH_PATH = Path("/tests/ground_truths/two_city_empire/ground_truth.json")
SCORE_PATH = Path("/logs/verifier/scores/two_city_empire.txt")
EXPECTED_CITY_IDS = {"city_alpha", "city_beta"}


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


def test_has_expected_top_level_fields(solution):
    assert "cities" in solution, "Solution missing 'cities'"
    assert isinstance(solution["cities"], dict), "'cities' must be a dict"
    assert set(solution["cities"].keys()) == EXPECTED_CITY_IDS, \
        f"'cities' must contain exactly {sorted(EXPECTED_CITY_IDS)}"
    assert "total_adjacency" in solution, "Solution missing 'total_adjacency'"
    assert isinstance(solution["total_adjacency"], (int, float)), "'total_adjacency' must be numeric"


def test_city_entries_have_required_fields(solution):
    for city_id, city in solution["cities"].items():
        assert isinstance(city, dict), f"{city_id} must be an object"
        assert "center" in city, f"{city_id} missing 'center'"
        assert isinstance(city["center"], list) and len(city["center"]) == 2, \
            f"{city_id}.center must be [x, y]"
        assert "placements" in city and isinstance(city["placements"], dict), \
            f"{city_id}.placements must be a dict"
        assert "adjacency_bonuses" in city and isinstance(city["adjacency_bonuses"], dict), \
            f"{city_id}.adjacency_bonuses must be a dict"
        assert "total_adjacency" in city and isinstance(city["total_adjacency"], (int, float)), \
            f"{city_id}.total_adjacency must be numeric"


def test_city_totals_sum_to_global_total(solution):
    city_total = sum(city["total_adjacency"] for city in solution["cities"].values())
    assert city_total == solution["total_adjacency"], \
        f"Global total_adjacency {solution['total_adjacency']} != city total {city_total}"


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
