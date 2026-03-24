#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/tests/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import DistrictType, Tile, get_placement_rules, validate_district_count, validate_district_uniqueness


SCENARIO_PATH = Path("/data/disaster_retrofit_basin/scenario.json")
OUTPUT_PATH = Path("/output/retrofit_plan.json")
SCORE_PATH = Path("/logs/verifier/scores/score.txt")


def write_score(value: float) -> None:
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(f"{value:.3f}")


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


def build_tiles(tile_rows):
    tiles = {}
    for row in tile_rows:
        tile = Tile(
            x=row["x"],
            y=row["y"],
            terrain=row.get("terrain", "GRASS"),
            feature=row.get("feature"),
            is_hills=row.get("is_hills", False),
            is_floodplains=row.get("is_floodplains", False),
            river_edges=row.get("river_edges", []),
            river_names=row.get("river_names", []),
            resource=row.get("resource"),
            resource_type=row.get("resource_type"),
            improvement=row.get("improvement"),
        )
        tiles[(tile.x, tile.y)] = tile
    return tiles


def per_district_by_name(per_district):
    result = {}
    for key, value in per_district.items():
        district_name = key.split("@", 1)[0]
        result[district_name] = value.total_bonus
    return result


def candidate_sort_key(candidate):
    final = candidate["final_districts"]
    ordered = tuple(tuple(final[name]) for name in sorted(final))
    return (-candidate["total_adjacency"], ordered)


def build_expected_solution(scenario):
    tiles = build_tiles(scenario["tiles"])
    center = tuple(scenario["city"]["center"])
    population = scenario["city"]["population"]
    existing = {name: tuple(coords) for name, coords in scenario["existing_districts"].items()}
    movable = list(scenario["movable_districts"])
    disabled = {tuple(coords) for coords in scenario["disabled_tiles"]}

    rules = get_placement_rules(tiles, center, population)
    calculator = get_adjacency_calculator(tiles)

    placements = {center: DistrictType.CITY_CENTER}
    final_districts = {}
    for district_name, coord in existing.items():
        if district_name not in movable:
            placements[coord] = getattr(DistrictType, district_name)
            final_districts[district_name] = coord

    best = None

    def search(index):
        nonlocal best
        if index == len(movable):
            moved_districts = {}
            for district_name in movable:
                original = list(existing[district_name])
                current = list(final_districts[district_name])
                if current != original:
                    moved_districts[district_name] = {"from": original, "to": current}

            if len(moved_districts) > scenario["move_budget"]:
                return

            district_map = {name: list(final_districts[name]) for name in existing}
            valid_count, count_errors = validate_district_count(district_map, population)
            assert valid_count, "; ".join(count_errors)
            valid_unique, unique_errors = validate_district_uniqueness(district_map)
            assert valid_unique, "; ".join(unique_errors)

            total, per_district = calculator.calculate_total_adjacency(placements)
            candidate = {
                "city_center": list(center),
                "final_districts": district_map,
                "moved_districts": moved_districts,
                "district_adjacency": per_district_by_name(per_district),
                "total_adjacency": total,
            }

            if best is None or candidate_sort_key(candidate) < candidate_sort_key(best):
                best = candidate
            return

        district_name = movable[index]
        district_type = getattr(DistrictType, district_name)

        for coord in sorted(tiles):
            if coord in disabled or coord in placements:
                continue
            result = rules.validate_placement(district_type, coord[0], coord[1], placements)
            if not result.valid:
                continue

            placements[coord] = district_type
            final_districts[district_name] = coord
            search(index + 1)
            del placements[coord]
            del final_districts[district_name]

    search(0)
    assert best is not None, "No legal retrofit plan exists for the scenario"
    return best


def validate_actual_output(actual, scenario):
    tiles = build_tiles(scenario["tiles"])
    center = tuple(scenario["city"]["center"])
    population = scenario["city"]["population"]
    existing = scenario["existing_districts"]
    movable = set(scenario["movable_districts"])
    disabled = {tuple(coords) for coords in scenario["disabled_tiles"]}

    assert isinstance(actual, dict), "Output must be a JSON object"
    assert actual.get("city_center") == list(center), "city_center must match the fixed scenario center"
    assert isinstance(actual.get("final_districts"), dict), "Missing or invalid final_districts"
    assert isinstance(actual.get("moved_districts"), dict), "Missing or invalid moved_districts"
    assert isinstance(actual.get("district_adjacency"), dict), "Missing or invalid district_adjacency"
    assert isinstance(actual.get("total_adjacency"), int), "Missing or invalid total_adjacency"

    assert set(actual["final_districts"].keys()) == set(existing.keys()), \
        "final_districts must contain exactly the scenario districts"

    placements = {center: DistrictType.CITY_CENTER}
    for district_name, coords in actual["final_districts"].items():
        assert isinstance(coords, list) and len(coords) == 2 and all(isinstance(v, int) for v in coords), \
            f"{district_name} must use [x, y] integer coordinates"
        coord = tuple(coords)
        assert coord not in disabled, f"{district_name} cannot be placed on a disabled tile"

        if district_name not in movable:
            assert coords == existing[district_name], f"{district_name} is locked and must remain in place"

        district_type = getattr(DistrictType, district_name)
        rules = get_placement_rules(tiles, center, population)
        result = rules.validate_placement(district_type, coord[0], coord[1], placements)
        assert result.valid, f"{district_name} invalid: {'; '.join(result.errors)}"
        placements[coord] = district_type

    expected_moved = {}
    for district_name in movable:
        original = existing[district_name]
        final = actual["final_districts"][district_name]
        if final != original:
            expected_moved[district_name] = {"from": original, "to": final}

    assert actual["moved_districts"] == expected_moved, "moved_districts must exactly match changed movable districts"
    assert len(actual["moved_districts"]) <= scenario["move_budget"], "Move budget exceeded"

    valid_count, count_errors = validate_district_count(actual["final_districts"], population)
    assert valid_count, "; ".join(count_errors)
    valid_unique, unique_errors = validate_district_uniqueness(actual["final_districts"])
    assert valid_unique, "; ".join(unique_errors)

    calculator = get_adjacency_calculator(tiles)
    total, per_district = calculator.calculate_total_adjacency(placements)
    expected_adjacency = per_district_by_name(per_district)

    assert actual["district_adjacency"] == expected_adjacency, \
        f"district_adjacency mismatch: expected {expected_adjacency}, got {actual['district_adjacency']}"
    assert actual["total_adjacency"] == sum(actual["district_adjacency"].values()), \
        "total_adjacency must equal the sum of district_adjacency"
    assert actual["total_adjacency"] == total, \
        f"total_adjacency mismatch: expected {total}, got {actual['total_adjacency']}"


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_retrofit_plan_matches_optimal_solution():
    scenario = load_json(SCENARIO_PATH)
    actual = load_json(OUTPUT_PATH)
    validate_actual_output(actual, scenario)

    expected = build_expected_solution(scenario)
    assert actual == expected, f"Retrofit plan mismatch.\nExpected: {expected}\nActual: {actual}"
    write_score(1.0)
