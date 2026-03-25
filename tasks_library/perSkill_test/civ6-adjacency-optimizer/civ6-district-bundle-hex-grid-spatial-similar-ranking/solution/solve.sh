#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from itertools import combinations, product
from pathlib import Path


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


data_dir = Path(os.environ.get("TASK_DATA_DIR", "/data"))
output_dir = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
scenario_path = data_dir / "bundle_scenario.json"
output_path = output_dir / "civ6_bundle_plan.json"

scenario = json.loads(scenario_path.read_text())
tile_map = {
    (tile["x"], tile["y"]): {"buildable": tile["buildable"], "tags": tile["tags"]}
    for tile in scenario["tiles"]
}

bundle_size = scenario["required_bundle_size"]
candidates = scenario["candidate_districts"]
buildable_tiles = [coord for coord, tile in tile_map.items() if tile["buildable"]]

best_total = None
best_payload = None

for district_combo in combinations(candidates, bundle_size):
    valid_sites = {
        district: [coord for coord in buildable_tiles if is_valid_placement(district, coord, scenario, tile_map)]
        for district in district_combo
    }
    for locations in product(*(valid_sites[district] for district in district_combo)):
        if len(set(locations)) != bundle_size:
            continue
        placements = dict(zip(district_combo, locations))
        per_district = {
            district: score_district(district, location, placements, scenario, tile_map)
            for district, location in placements.items()
        }
        total = sum(per_district.values())
        normalized = {
            district: {
                "district": district,
                "location": list(placements[district]),
                "adjacency": per_district[district],
            }
            for district in sorted(placements)
        }
        if best_total is None or total > best_total:
            best_total = total
            best_payload = normalized

output_dir.mkdir(parents=True, exist_ok=True)
result = {
    "city_center": scenario["city_center"],
    "chosen_districts": [best_payload[district] for district in sorted(best_payload)],
    "total_adjacency": best_total,
}
output_path.write_text(json.dumps(result, indent=2))
print(f"Wrote {output_path} with total_adjacency={best_total}")
PY
