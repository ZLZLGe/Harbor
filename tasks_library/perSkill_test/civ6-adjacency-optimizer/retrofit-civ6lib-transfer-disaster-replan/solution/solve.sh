#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, "/solution/src")

from adjacency_rules import get_adjacency_calculator
from placement_rules import DistrictType, Tile, get_placement_rules


SCENARIO_PATH = Path("/data/disaster_retrofit_basin/scenario.json")
OUTPUT_PATH = Path("/output/retrofit_plan.json")


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


def adjacency_by_name(per_district):
    values = {}
    for key, result in per_district.items():
        district_name = key.split("@", 1)[0]
        values[district_name] = result.total_bonus
    return values


def candidate_sort_key(candidate):
    final = candidate["final_districts"]
    ordered = tuple(tuple(final[name]) for name in sorted(final))
    return (-candidate["total_adjacency"], ordered)


scenario = load_json(SCENARIO_PATH)
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
    global best
    if index == len(movable):
        moved_districts = {}
        for district_name in movable:
            original = list(existing[district_name])
            current = list(final_districts[district_name])
            if current != original:
                moved_districts[district_name] = {"from": original, "to": current}

        if len(moved_districts) > scenario["move_budget"]:
            return

        total, per_district = calculator.calculate_total_adjacency(placements)
        candidate = {
            "city_center": list(center),
            "final_districts": {name: list(final_districts[name]) for name in existing},
            "moved_districts": moved_districts,
            "district_adjacency": adjacency_by_name(per_district),
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

if best is None:
    raise SystemExit("No legal retrofit plan found")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w") as f:
    json.dump(best, f, indent=2)
PY
