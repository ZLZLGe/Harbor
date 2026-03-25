import json
import os
from itertools import combinations, product
from pathlib import Path


import pytest


DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
SCENARIO_PATH = DATA_DIR / "bundle_scenario.json"
OUTPUT_PATH = OUTPUT_DIR / "civ6_bundle_plan.json"


def neighbors(x, y):
    if y % 2 == 0:
        directions = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
    else:
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]
    return [(x + dx, y + dy) for dx, dy in directions]


def offset_to_cube(col, row):
    cube_x = col - (row - (row & 1)) // 2
    cube_z = row
    cube_y = -cube_x - cube_z
    return cube_x, cube_y, cube_z


def hex_distance(a, b):
    ax, ay, az = offset_to_cube(*a)
    bx, by, bz = offset_to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def build_tile_map(scenario):
    return {
        (tile["x"], tile["y"]): {"buildable": tile["buildable"], "tags": tile["tags"]}
        for tile in scenario["tiles"]
    }


def is_valid_placement(district, location, scenario, tile_map):
    center = tuple(scenario["city_center"])
    radius = scenario["city_radius"]
    rules = scenario["district_rules"][district]
    tile = tile_map.get(location)
    if tile is None or not tile["buildable"]:
        return False
    if location == center:
        return False
    if hex_distance(center, location) > radius:
        return False
    tags = set(tile["tags"])
    required = rules["requires_any_of_self_tags"]
    if required and not any(tag in tags for tag in required):
        return False
    if any(tag in tags for tag in rules["forbidden_self_tags"]):
        return False
    return True


def score_district(district, location, placements, scenario, tile_map):
    rules = scenario["district_rules"][district]
    occupied = {loc for loc in placements.values()}
    total = 0
    for neighbor in neighbors(*location):
        if neighbor in occupied and neighbor != location:
            total += rules["adjacent_district_bonus"]
            continue
        tile = tile_map.get(neighbor)
        if tile is None:
            continue
        for tag in tile["tags"]:
            total += rules["adjacency_from_neighbor_tags"].get(tag, 0)
    return total


def compute_optimal_total(scenario, tile_map):
    candidates = scenario["candidate_districts"]
    bundle_size = scenario["required_bundle_size"]
    buildable_tiles = [coord for coord, tile in tile_map.items() if tile["buildable"]]
    best_total = None
    for district_combo in combinations(candidates, bundle_size):
        valid_sites = {
            district: [coord for coord in buildable_tiles if is_valid_placement(district, coord, scenario, tile_map)]
            for district in district_combo
        }
        for locations in product(*(valid_sites[district] for district in district_combo)):
            if len(set(locations)) != bundle_size:
                continue
            placements = dict(zip(district_combo, locations))
            total = sum(
                score_district(district, location, placements, scenario, tile_map)
                for district, location in placements.items()
            )
            if best_total is None or total > best_total:
                best_total = total
    return best_total


@pytest.fixture(scope="session")
def scenario():
    return json.loads(SCENARIO_PATH.read_text())


@pytest.fixture(scope="session")
def tile_map(scenario):
    return build_tile_map(scenario)


@pytest.fixture(scope="session")
def output():
    return json.loads(OUTPUT_PATH.read_text())


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"缺少输出文件: {OUTPUT_PATH}"


def test_output_shape(output, scenario):
    assert isinstance(output, dict)
    assert output.get("city_center") == scenario["city_center"]
    assert isinstance(output.get("chosen_districts"), list)
    assert len(output["chosen_districts"]) == scenario["required_bundle_size"]
    assert isinstance(output.get("total_adjacency"), int)


def test_chosen_district_fields(output, scenario):
    seen_names = set()
    seen_locations = set()
    candidates = set(scenario["candidate_districts"])
    for item in output["chosen_districts"]:
        assert set(item.keys()) == {"district", "location", "adjacency"}
        assert item["district"] in candidates
        assert item["district"] not in seen_names
        seen_names.add(item["district"])
        assert isinstance(item["location"], list) and len(item["location"]) == 2
        assert all(isinstance(value, int) for value in item["location"])
        location = tuple(item["location"])
        assert location not in seen_locations
        seen_locations.add(location)
        assert isinstance(item["adjacency"], int)


def test_placements_are_legal(output, scenario, tile_map):
    placements = {
        item["district"]: tuple(item["location"])
        for item in output["chosen_districts"]
    }
    for district, location in placements.items():
        assert is_valid_placement(district, location, scenario, tile_map), (
            f"{district} placed illegally at {location}"
        )


def test_adjacency_values_match_rules(output, scenario, tile_map):
    placements = {
        item["district"]: tuple(item["location"])
        for item in output["chosen_districts"]
    }
    expected_total = 0
    for item in output["chosen_districts"]:
        expected = score_district(
            item["district"],
            tuple(item["location"]),
            placements,
            scenario,
            tile_map,
        )
        assert item["adjacency"] == expected, (
            f"{item['district']} adjacency {item['adjacency']} != expected {expected}"
        )
        expected_total += expected
    assert output["total_adjacency"] == expected_total


def test_solution_is_globally_optimal(output, scenario, tile_map):
    optimal_total = compute_optimal_total(scenario, tile_map)
    assert output["total_adjacency"] == optimal_total, (
        f"total_adjacency {output['total_adjacency']} != optimal {optimal_total}"
    )
