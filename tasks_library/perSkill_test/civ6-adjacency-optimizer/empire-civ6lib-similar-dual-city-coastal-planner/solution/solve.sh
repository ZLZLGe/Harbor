#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, "/solution/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import Tile, DistrictType, get_placement_rules, validate_city_distances


SCENARIO_PATH = Path("/data/coastal_empire/scenario.json")
OUTPUT_PATH = Path("/output/dual_city_plan.json")


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
            districts = {district_name: list(coord) for coord, district_name in current.items()}
            layouts.append(
                {
                    "city_id": role["city_id"],
                    "center": list(center),
                    "districts": districts,
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
            tuple(sorted((name, tuple(coords)) for name, coords in layout["districts"].items())),
        )
    )
    return layouts


def build_plan(city_layouts, tiles, calculator):
    placements = {}
    district_adjacency = {}
    owner_by_position = {}

    for city in city_layouts:
        center = tuple(city["center"])
        placements[center] = DistrictType.CITY_CENTER
        for district_name, coords in city["districts"].items():
            coord = tuple(coords)
            placements[coord] = getattr(DistrictType, district_name)
            owner_by_position[(coord, district_name)] = f"{city['city_id']}:{district_name}"

    total, per_district = calculator.calculate_total_adjacency(placements)
    for key, result in per_district.items():
        district_name, raw_coord = key.split("@", 1)
        coord = tuple(int(part) for part in raw_coord.strip("()").split(","))
        owner_key = owner_by_position[(coord, district_name)]
        district_adjacency[owner_key] = result.total_bonus

    return {
        "cities": sorted(city_layouts, key=lambda city: city["city_id"]),
        "district_adjacency": dict(sorted(district_adjacency.items())),
        "total_adjacency": total,
    }


with SCENARIO_PATH.open() as f:
    scenario = json.load(f)

tiles = build_tiles(scenario["tiles"])
calculator = get_adjacency_calculator(tiles)
roles = scenario["city_roles"]

layout_cache = {}
for role in roles:
    for center in role["candidate_centers"]:
        layout_cache[(role["city_id"], tuple(center))] = enumerate_city_layouts(
            role, tuple(center), tiles, calculator
        )

best_plan = None
best_total = -1

for chosen_centers in product(*[role["candidate_centers"] for role in roles]):
    centers = [tuple(center) for center in chosen_centers]
    if len(set(centers)) != len(centers):
        continue
    valid_distance, _ = validate_city_distances(centers, tiles)
    if not valid_distance:
        continue

    selected_layouts = []
    for role, center in zip(roles, centers):
        layouts = layout_cache[(role["city_id"], center)]
        selected_layouts.append(layouts[0])

    plan = build_plan(selected_layouts, tiles, calculator)
    if plan["total_adjacency"] > best_total:
        best_total = plan["total_adjacency"]
        best_plan = plan

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w") as f:
    json.dump(best_plan, f, indent=2)

print(json.dumps({"written_to": str(OUTPUT_PATH), "total_adjacency": best_total}, indent=2))
PY
