#!/usr/bin/env python3

import json
from pathlib import Path

import pytest


TASK_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = Path("/data/weighted_reserve_scenario.json")
if not SCENARIO_PATH.exists():
    SCENARIO_PATH = TASK_ROOT / "environment/data/weighted_reserve_scenario.json"

OUTPUT_PATH = Path("/output/civ6_weighted_reserve_plan.json")
if not OUTPUT_PATH.exists():
    OUTPUT_PATH = TASK_ROOT / ".tmp_output/civ6_weighted_reserve_plan.json"

SCORE_PATH = Path("/logs/verifier/scores/weighted_reserve_plan.txt")
if not SCORE_PATH.parent.exists():
    SCORE_PATH = TASK_ROOT / ".tmp_logs/verifier/scores/weighted_reserve_plan.txt"

DIRECTIONS_EVEN = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
DIRECTIONS_ODD = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]
NON_SPECIALTY = {"AQUEDUCT", "DAM", "CANAL", "SPACEPORT", "NEIGHBORHOOD"}
DESTRUCTIBLE = {"FEATURE_FOREST", "FEATURE_JUNGLE", "FEATURE_MARSH"}


def get_neighbors(x, y):
    directions = DIRECTIONS_ODD if y % 2 == 1 else DIRECTIONS_EVEN
    return [(x + dx, y + dy) for dx, dy in directions]


def hex_distance(a, b):
    def to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    ax, ay, az = to_cube(*a)
    bx, by, bz = to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def is_water(tile):
    return tile["terrain"] in ("COAST", "OCEAN", "LAKE")


def is_mountain(tile):
    return tile["terrain"] == "MOUNTAIN"


def has_river(tile):
    return bool(tile.get("river_edges", []))


def specialty_limit(population):
    return 1 + (population - 1) // 3


def build_index(tiles):
    return {(tile["x"], tile["y"]): tile for tile in tiles}


def is_valid_placement(build_name, coord, scenario, placements):
    city_center = tuple(scenario["city_center"])
    reserved = {tuple(tile) for tile in scenario["reserved_tiles"]}
    tiles = build_index(scenario["tiles"])
    tile = tiles.get(coord)
    if tile is None or coord == city_center or coord in reserved:
        return False, "build placed on an invalid or reserved tile"
    if coord in placements.values():
        return False, "two builds overlap on the same tile"
    if hex_distance(city_center, coord) > 3:
        return False, "build is more than 3 tiles away from the city center"
    if is_mountain(tile):
        return False, "district cannot be placed on a mountain"
    if tile.get("feature") == "FEATURE_GEOTHERMAL_FISSURE":
        return False, "district cannot be placed on a geothermal fissure"

    if build_name == "HARBOR":
        if tile["terrain"] not in ("COAST", "LAKE"):
            return False, "harbor must be on coast or lake"
        if not any(
            neighbor in tiles and not is_water(tiles[neighbor])
            for neighbor in get_neighbors(*coord)
        ):
            return False, "harbor must be adjacent to land"
    elif is_water(tile):
        return False, "land district cannot be placed on water"

    if build_name == "AQUEDUCT":
        if hex_distance(city_center, coord) != 1:
            return False, "aqueduct must be adjacent to the city center"
        has_fresh_water = has_river(tile)
        for neighbor in get_neighbors(*coord):
            neighbor_tile = tiles.get(neighbor)
            if neighbor_tile is None:
                continue
            if (
                is_mountain(neighbor_tile)
                or neighbor_tile["terrain"] == "LAKE"
                or neighbor_tile.get("feature") == "FEATURE_OASIS"
                or has_river(neighbor_tile)
            ):
                has_fresh_water = True
                break
        if not has_fresh_water:
            return False, "aqueduct needs a fresh water source"

    if build_name == "DAM":
        if not tile.get("is_floodplains"):
            return False, "dam must be on floodplains"
        if len(tile.get("river_edges", [])) < 2:
            return False, "dam needs a river crossing at least two edges"

    return True, ""


def apply_destruction(tiles, full_placements):
    updated = {}
    for coord, tile in tiles.items():
        new_tile = dict(tile)
        if (
            full_placements.get(coord) not in (None, "CITY_CENTER")
            and new_tile.get("feature") in DESTRUCTIBLE
        ):
            new_tile["feature"] = None
        updated[coord] = new_tile
    return updated


def raw_adjacency(build_name, coord, city_center, modified_tiles, full_placements):
    bonus = 0

    if build_name == "CAMPUS":
        rainforest = 0
        generic_districts = 0
        for neighbor in get_neighbors(*coord):
            tile = modified_tiles.get(neighbor)
            if tile is not None:
                if tile.get("feature") == "FEATURE_GEOTHERMAL_FISSURE":
                    bonus += 2
                if tile.get("feature") == "FEATURE_REEF":
                    bonus += 2
                if is_mountain(tile):
                    bonus += 1
                if tile.get("feature") == "FEATURE_JUNGLE":
                    rainforest += 1
            if neighbor == city_center or neighbor in full_placements:
                generic_districts += 1
        return bonus + rainforest // 2 + generic_districts // 2

    if build_name == "HOLY_SITE":
        forest = 0
        generic_districts = 0
        for neighbor in get_neighbors(*coord):
            tile = modified_tiles.get(neighbor)
            if tile is not None and is_mountain(tile):
                bonus += 1
            if tile is not None and tile.get("feature") == "FEATURE_FOREST":
                forest += 1
            if neighbor == city_center or neighbor in full_placements:
                generic_districts += 1
        return bonus + forest // 2 + generic_districts // 2

    if build_name == "INDUSTRIAL_ZONE":
        generic_districts = 0
        for neighbor in get_neighbors(*coord):
            if full_placements.get(neighbor) in {"AQUEDUCT", "DAM", "CANAL", "BATH"}:
                bonus += 2
            elif neighbor == city_center or neighbor in full_placements:
                generic_districts += 1
        return bonus + generic_districts // 2

    if build_name == "COMMERCIAL_HUB":
        generic_districts = 0
        if has_river(modified_tiles[coord]):
            bonus += 2
        for neighbor in get_neighbors(*coord):
            if full_placements.get(neighbor) == "HARBOR":
                bonus += 2
            elif neighbor == city_center or neighbor in full_placements:
                generic_districts += 1
        return bonus + generic_districts // 2

    if build_name == "HARBOR":
        generic_districts = 0
        for neighbor in get_neighbors(*coord):
            if neighbor == city_center:
                bonus += 2
            elif neighbor in full_placements:
                generic_districts += 1
        return bonus + generic_districts // 2

    return 0


def evaluate_solution(scenario, solution):
    required = scenario["required_builds"]
    weights = scenario["weights"]
    city_center = tuple(scenario["city_center"])
    tiles = build_index(scenario["tiles"])

    placements = solution["placements"]
    specialty_count = sum(1 for name in placements if name not in NON_SPECIALTY)
    if specialty_count > specialty_limit(scenario["population"]):
        raise AssertionError("specialty district count exceeds the population cap")

    placed_coords = {}
    for build_name in required:
        coord = tuple(placements[build_name])
        valid, message = is_valid_placement(build_name, coord, scenario, placed_coords)
        assert valid, f"{build_name}: {message}"
        placed_coords[build_name] = coord

    full_placements = {coord: name for name, coord in placed_coords.items()}
    modified_tiles = apply_destruction(tiles, full_placements)

    expected_scores = {}
    total_weighted_score = 0
    for build_name in required:
        coord = placed_coords[build_name]
        raw = raw_adjacency(build_name, coord, city_center, modified_tiles, full_placements)
        weight = weights[build_name]
        weighted = raw * weight
        expected_scores[build_name] = {
            "raw_adjacency": raw,
            "weight": weight,
            "weighted_score": weighted,
        }
        total_weighted_score += weighted

    return expected_scores, total_weighted_score


def find_optimal_total(scenario):
    required = scenario["required_builds"]
    population = scenario["population"]
    specialty_builds = [name for name in required if name not in NON_SPECIALTY]
    assert len(specialty_builds) <= specialty_limit(population)

    tiles = build_index(scenario["tiles"])
    candidates = {}
    for build_name in required:
        options = []
        for coord in tiles:
            valid, _ = is_valid_placement(build_name, coord, scenario, {})
            if valid:
                options.append(coord)
        candidates[build_name] = options

    order = sorted(required, key=lambda name: len(candidates[name]))
    best_total = -1

    def backtrack(index, placements):
        nonlocal best_total
        if index == len(order):
            per_build_scores, total = evaluate_solution(
                scenario,
                {
                    "placements": {name: list(coord) for name, coord in placements.items()}
                },
            )
            best_total = max(best_total, total)
            return

        build_name = order[index]
        for coord in candidates[build_name]:
            if coord in placements.values():
                continue
            valid, _ = is_valid_placement(build_name, coord, scenario, placements)
            if not valid:
                continue
            placements[build_name] = coord
            backtrack(index + 1, placements)
            del placements[build_name]

    backtrack(0, {})
    return best_total


@pytest.fixture(scope="session")
def scenario():
    with SCENARIO_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def solution():
    assert OUTPUT_PATH.exists(), f"solution file not found: {OUTPUT_PATH}"
    with OUTPUT_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def optimal_total(scenario):
    return find_optimal_total(scenario)


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), f"solution file not found: {OUTPUT_PATH}"


def test_output_is_json_object(solution):
    assert isinstance(solution, dict)


def test_required_fields_exist(solution):
    assert "city_center" in solution
    assert "placements" in solution
    assert "district_scores" in solution
    assert "total_weighted_score" in solution


def test_city_center_matches_scenario(solution, scenario):
    assert solution["city_center"] == scenario["city_center"]


def test_build_sets_match_scenario(solution, scenario):
    required = set(scenario["required_builds"])
    assert set(solution["placements"]) == required
    assert set(solution["district_scores"]) == required


def test_coordinate_shapes(solution):
    for coord in solution["placements"].values():
        assert isinstance(coord, list)
        assert len(coord) == 2
        assert all(isinstance(value, int) for value in coord)


def test_reported_scores_match_recomputed_scores(solution, scenario):
    expected_scores, total_weighted_score = evaluate_solution(scenario, solution)
    assert solution["district_scores"] == expected_scores
    assert solution["total_weighted_score"] == total_weighted_score


def test_weight_fields_match_scenario(solution, scenario):
    for build_name, details in solution["district_scores"].items():
        assert details["weight"] == scenario["weights"][build_name]
        assert details["weighted_score"] == details["raw_adjacency"] * details["weight"]


def test_solution_is_optimal(solution, optimal_total, scenario):
    expected_scores, actual_total = evaluate_solution(scenario, solution)
    score = actual_total / optimal_total if optimal_total > 0 else 0.0
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(str(score))
    assert actual_total == optimal_total, (
        f"submitted total_weighted_score {actual_total} != optimal {optimal_total}"
    )
