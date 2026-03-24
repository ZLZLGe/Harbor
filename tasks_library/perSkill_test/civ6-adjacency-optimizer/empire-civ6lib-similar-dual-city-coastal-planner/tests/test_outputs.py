#!/usr/bin/env python3

import json
import sys
from itertools import product
from pathlib import Path

import pytest

sys.path.insert(0, "/tests/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import (
    Tile,
    DistrictType,
    get_placement_rules,
    validate_city_distances,
    validate_district_count,
    validate_district_uniqueness,
)


SCENARIO_PATH = Path("/data/coastal_empire/scenario.json")
OUTPUT_PATH = Path("/output/dual_city_plan.json")
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


def validate_solution_structure(solution, scenario, tiles):
    assert isinstance(solution, dict), "Output must be a JSON object"
    assert "cities" in solution and isinstance(solution["cities"], list), "Missing or invalid 'cities'"
    assert "district_adjacency" in solution and isinstance(solution["district_adjacency"], dict), \
        "Missing or invalid 'district_adjacency'"
    assert "total_adjacency" in solution and isinstance(solution["total_adjacency"], int), \
        "Missing or invalid 'total_adjacency'"

    role_by_id = {role["city_id"]: role for role in scenario["city_roles"]}
    assert len(solution["cities"]) == len(role_by_id), "Incorrect number of cities"

    seen_ids = set()
    centers = []
    normalized_cities = []

    for city in solution["cities"]:
        assert isinstance(city, dict), "Each city entry must be an object"
        city_id = city.get("city_id")
        assert city_id in role_by_id, f"Unknown city_id: {city_id}"
        assert city_id not in seen_ids, f"Duplicate city_id: {city_id}"
        seen_ids.add(city_id)

        center = city.get("center")
        assert isinstance(center, list) and len(center) == 2 and all(isinstance(v, int) for v in center), \
            f"{city_id}: invalid center coordinates"
        assert center in role_by_id[city_id]["candidate_centers"], \
            f"{city_id}: center must be chosen from candidate_centers"
        centers.append(tuple(center))

        districts = city.get("districts")
        assert isinstance(districts, dict), f"{city_id}: missing or invalid districts map"
        expected = set(role_by_id[city_id]["required_districts"])
        actual = set(districts.keys())
        assert actual == expected, f"{city_id}: districts must exactly match required_districts"

        for district_name, coords in districts.items():
            assert isinstance(coords, list) and len(coords) == 2 and all(isinstance(v, int) for v in coords), \
                f"{city_id}:{district_name} must use [x, y] integer coordinates"

        normalized_cities.append(
            {
                "city_id": city_id,
                "center": tuple(center),
                "districts": {name: tuple(coords) for name, coords in districts.items()},
            }
        )

    valid_distance, distance_errors = validate_city_distances(centers, tiles)
    assert valid_distance, "; ".join(distance_errors)

    calculator = get_adjacency_calculator(tiles)
    placements = {tuple(city["center"]): DistrictType.CITY_CENTER for city in solution["cities"]}
    owner_by_position = {}

    for city in sorted(normalized_cities, key=lambda item: item["city_id"]):
        role = role_by_id[city["city_id"]]
        rules = get_placement_rules(tiles, city["center"], role["population"])

        raw_districts = {name: list(coords) for name, coords in city["districts"].items()}
        valid_count, count_errors = validate_district_count(raw_districts, role["population"])
        assert valid_count, "; ".join(count_errors)

        valid_unique, unique_errors = validate_district_uniqueness(raw_districts, city_id=city["city_id"])
        assert valid_unique, "; ".join(unique_errors)

        for district_name in sorted(city["districts"]):
            coord = city["districts"][district_name]
            district_type = getattr(DistrictType, district_name)
            result = rules.validate_placement(district_type, coord[0], coord[1], placements)
            assert result.valid, f"{city['city_id']}:{district_name} invalid: {result.errors}"
            placements[coord] = district_type
            owner_by_position[(coord, district_name)] = f"{city['city_id']}:{district_name}"

    total, per_district = calculator.calculate_total_adjacency(placements)

    expected_adjacency = {}
    for key, result in per_district.items():
        district_name, raw_coord = key.split("@", 1)
        coord = tuple(int(part) for part in raw_coord.strip("()").split(","))
        owner_key = owner_by_position[(coord, district_name)]
        expected_adjacency[owner_key] = result.total_bonus

    assert set(solution["district_adjacency"].keys()) == set(expected_adjacency.keys()), \
        "district_adjacency keys must match all placed districts"
    assert solution["district_adjacency"] == expected_adjacency, \
        f"district_adjacency mismatch: expected {expected_adjacency}, got {solution['district_adjacency']}"
    assert solution["total_adjacency"] == sum(solution["district_adjacency"].values()), \
        "total_adjacency must equal the sum of district_adjacency"
    assert solution["total_adjacency"] == total, \
        f"total_adjacency mismatch: expected {total}, got {solution['total_adjacency']}"

    return {"total_adjacency": total}


def enumerate_city_layouts(role, center, tiles, calculator):
    rules = get_placement_rules(tiles, center, role["population"])
    base = {center: DistrictType.CITY_CENTER}
    valid_options = {}

    for district_name in role["required_districts"]:
        district_type = getattr(DistrictType, district_name)
        coords = []
        for coord in tiles:
            if coord == center:
                continue
            result = rules.validate_placement(district_type, coord[0], coord[1], base)
            if result.valid:
                coords.append(coord)
        valid_options[district_name] = coords

    order = sorted(role["required_districts"], key=lambda name: len(valid_options[name]))
    layouts = []
    current = {}

    def backtrack(idx):
        if idx == len(order):
            placements = {
                center: DistrictType.CITY_CENTER,
                **{coord: getattr(DistrictType, district_name) for coord, district_name in current.items()},
            }
            total, _ = calculator.calculate_total_adjacency(placements)
            layouts.append(
                {
                    "city_id": role["city_id"],
                    "center": center,
                    "districts": dict(current),
                    "local_total": total,
                }
            )
            return

        district_name = order[idx]
        district_type = getattr(DistrictType, district_name)
        existing = {
            center: DistrictType.CITY_CENTER,
            **{coord: getattr(DistrictType, name) for coord, name in current.items()},
        }

        for coord in valid_options[district_name]:
            if coord in current:
                continue
            result = rules.validate_placement(district_type, coord[0], coord[1], existing)
            if result.valid:
                current[coord] = district_name
                backtrack(idx + 1)
                del current[coord]

    backtrack(0)
    layouts.sort(
        key=lambda layout: (
            -layout["local_total"],
            tuple(layout["center"]),
            tuple(sorted((name, coord) for coord, name in layout["districts"].items())),
        )
    )
    return layouts


def compute_optimal_total(scenario, tiles):
    calculator = get_adjacency_calculator(tiles)
    roles = scenario["city_roles"]
    layout_cache = {}

    for role in roles:
        for center in role["candidate_centers"]:
            layouts = enumerate_city_layouts(role, tuple(center), tiles, calculator)
            layout_cache[(role["city_id"], tuple(center))] = layouts

    best_total = -1

    for chosen_centers in product(*[role["candidate_centers"] for role in roles]):
        centers = [tuple(center) for center in chosen_centers]
        if len(set(centers)) != len(centers):
            continue
        valid_distance, _ = validate_city_distances(centers, tiles)
        if not valid_distance:
            continue

        selected = []
        for role, center in zip(roles, centers):
            selected.append(layout_cache[(role["city_id"], center)][0])

        placements = {}
        for layout in selected:
            placements[layout["center"]] = DistrictType.CITY_CENTER
            for coord, district_name in layout["districts"].items():
                placements[coord] = getattr(DistrictType, district_name)

        total, _ = calculator.calculate_total_adjacency(placements)
        best_total = max(best_total, total)

    return best_total


@pytest.fixture(scope="session")
def scenario():
    return load_json(SCENARIO_PATH)


@pytest.fixture(scope="session")
def tiles(scenario):
    return build_tiles(scenario["tiles"])


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_output_is_optimal(scenario, tiles):
    solution = load_json(OUTPUT_PATH)
    validated = validate_solution_structure(solution, scenario, tiles)
    optimal_total = compute_optimal_total(scenario, tiles)
    assert validated["total_adjacency"] == optimal_total, \
        f"Plan is valid but suboptimal: got {validated['total_adjacency']}, expected {optimal_total}"
    write_score(1.0)
