#!/bin/bash

python3 <<'PY'
import json
from pathlib import Path


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
        return False
    if coord in placements.values():
        return False
    if hex_distance(city_center, coord) > 3:
        return False
    if is_mountain(tile):
        return False
    if tile.get("feature") == "FEATURE_GEOTHERMAL_FISSURE":
        return False

    if build_name == "HARBOR":
        if tile["terrain"] not in ("COAST", "LAKE"):
            return False
        if not any(
            neighbor in tiles and not is_water(tiles[neighbor])
            for neighbor in get_neighbors(*coord)
        ):
            return False
    elif is_water(tile):
        return False

    if build_name == "AQUEDUCT":
        if hex_distance(city_center, coord) != 1:
            return False
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
            return False

    if build_name == "DAM":
        if not tile.get("is_floodplains"):
            return False
        if len(tile.get("river_edges", [])) < 2:
            return False

    return True


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
        tile = modified_tiles[coord]
        generic_districts = 0
        if has_river(tile):
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


def evaluate_layout(scenario, placements):
    city_center = tuple(scenario["city_center"])
    weights = scenario["weights"]
    tiles = build_index(scenario["tiles"])
    full_placements = {tuple(coord): name for name, coord in placements.items()}
    modified_tiles = apply_destruction(tiles, full_placements)

    district_scores = {}
    total_weighted_score = 0
    for build_name in scenario["required_builds"]:
        coord = placements[build_name]
        raw = raw_adjacency(build_name, coord, city_center, modified_tiles, full_placements)
        weight = weights[build_name]
        weighted = raw * weight
        district_scores[build_name] = {
            "raw_adjacency": raw,
            "weight": weight,
            "weighted_score": weighted,
        }
        total_weighted_score += weighted

    return district_scores, total_weighted_score


def search_best(scenario):
    required = scenario["required_builds"]
    population = scenario["population"]
    city_center = tuple(scenario["city_center"])
    tiles = build_index(scenario["tiles"])

    specialty_builds = [name for name in required if name not in NON_SPECIALTY]
    if len(specialty_builds) > specialty_limit(population):
        raise ValueError("Scenario is infeasible under the specialty district limit.")

    candidates = {}
    for build_name in required:
        options = []
        for coord in tiles:
            if is_valid_placement(build_name, coord, scenario, {}):
                options.append(coord)
        candidates[build_name] = options

    order = sorted(required, key=lambda name: len(candidates[name]))
    best = None

    def backtrack(index, placements):
        nonlocal best
        if index == len(order):
            district_scores, total_weighted_score = evaluate_layout(scenario, placements)
            if best is None or total_weighted_score > best["total_weighted_score"]:
                best = {
                    "city_center": list(city_center),
                    "placements": {name: list(placements[name]) for name in required},
                    "district_scores": district_scores,
                    "total_weighted_score": total_weighted_score,
                }
            return

        build_name = order[index]
        for coord in candidates[build_name]:
            if coord in placements.values():
                continue
            if not is_valid_placement(build_name, coord, scenario, placements):
                continue
            placements[build_name] = coord
            backtrack(index + 1, placements)
            del placements[build_name]

    backtrack(0, {})
    return best


scenario_path = Path("/data/weighted_reserve_scenario.json")
if not scenario_path.exists():
    scenario_path = Path.cwd() / "environment/data/weighted_reserve_scenario.json"

output_root = Path("/output") if Path("/output").exists() else Path.cwd() / ".tmp_output"
output_path = output_root / "civ6_weighted_reserve_plan.json"

with scenario_path.open() as f:
    scenario = json.load(f)

solution = search_best(scenario)

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w") as f:
    json.dump(solution, f, indent=2)

print(f"Wrote optimal weighted reserve plan to {output_path}")
print(f"total_weighted_score = {solution['total_weighted_score']}")
PY
