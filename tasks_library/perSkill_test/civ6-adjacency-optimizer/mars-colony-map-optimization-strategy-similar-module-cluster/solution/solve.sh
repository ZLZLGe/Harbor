#!/bin/bash
set -euo pipefail

SCENARIO_PATH="${SCENARIO_PATH:-/data/mars_scenario.json}"
OUTPUT_PATH="${OUTPUT_PATH:-/output/mars_colony_plan.json}"
export SCENARIO_PATH OUTPUT_PATH

python3 - <<'PY'
import json
import os
from itertools import combinations
from pathlib import Path


DIRECTIONS_EVEN_ROW = [
    (1, 0),
    (0, -1),
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
]

DIRECTIONS_ODD_ROW = [
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (0, 1),
    (1, 1),
]

TYPE_ORDER = {"RESEARCH": 0, "INDUSTRIAL": 1, "LIFE_SUPPORT": 2}


def get_neighbors(coord):
    x, y = coord
    directions = DIRECTIONS_ODD_ROW if y % 2 == 1 else DIRECTIONS_EVEN_ROW
    return [(x + dx, y + dy) for dx, dy in directions]


def hex_distance(a, b):
    def offset_to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    ax, ay, az = offset_to_cube(*a)
    bx, by, bz = offset_to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def score_module(module_type, coord, dome, placements, markers_by_coord):
    adjacent = get_neighbors(coord)
    adjacent_markers = []
    for neighbor in adjacent:
        adjacent_markers.extend(markers_by_coord.get(neighbor, []))

    score = 0
    if dome in adjacent:
        score += 1

    if module_type == "RESEARCH":
        score += 2 * adjacent_markers.count("science_site")
        score += sum(
            1
            for other_type, other_coord in placements
            if other_type == "LIFE_SUPPORT" and other_coord in adjacent
        )
    elif module_type == "INDUSTRIAL":
        score += 2 * adjacent_markers.count("ore_field")
        score += adjacent_markers.count("power_node")
    elif module_type == "LIFE_SUPPORT":
        score += 2 * adjacent_markers.count("ice_vent")
        score += sum(
            1
            for other_type, other_coord in placements
            if other_type == "RESEARCH" and other_coord in adjacent
        )
    else:
        raise ValueError(f"Unknown module type: {module_type}")

    return score


scenario_path = Path(os.environ["SCENARIO_PATH"])
output_path = Path(os.environ["OUTPUT_PATH"])

with open(scenario_path) as f:
    scenario = json.load(f)

tiles = {(tile["x"], tile["y"]): tile for tile in scenario["tiles"]}
markers_by_coord = {
    coord: list(tile.get("markers", []))
    for coord, tile in tiles.items()
}
buildable = {
    coord: tile
    for coord, tile in tiles.items()
    if tile.get("buildable", False)
}

terrain_rules = scenario["terrain_rules"]
module_costs = scenario["module_costs"]
supply_radius = scenario["supply_radius"]

command_candidates = sorted(
    coord
    for coord, tile in buildable.items()
    if tile["terrain"] in terrain_rules["command_dome"]
)

best_total = -1
best_tiebreak = None
best_plan = None

for dome in command_candidates:
    in_range = sorted(
        coord
        for coord in buildable
        if coord != dome and hex_distance(dome, coord) <= supply_radius
    )
    research_candidates = [
        coord for coord in in_range
        if buildable[coord]["terrain"] in terrain_rules["RESEARCH"]
    ]
    industrial_candidates = [
        coord for coord in in_range
        if buildable[coord]["terrain"] in terrain_rules["INDUSTRIAL"]
    ]
    life_candidates = [
        coord for coord in in_range
        if buildable[coord]["terrain"] in terrain_rules["LIFE_SUPPORT"]
    ]

    for research in research_candidates:
        for industrial in industrial_candidates:
            if industrial == research:
                continue
            remaining_life = [
                coord for coord in life_candidates
                if coord not in {research, industrial}
            ]
            for life_positions in combinations(remaining_life, 2):
                placements = [
                    ("RESEARCH", research),
                    ("INDUSTRIAL", industrial),
                    ("LIFE_SUPPORT", life_positions[0]),
                    ("LIFE_SUPPORT", life_positions[1]),
                ]

                if any(
                    life_coord in get_neighbors(industrial)
                    for life_coord in life_positions
                ):
                    continue

                population_used = sum(module_costs[module_type] for module_type, _ in placements)
                if population_used > scenario["population_slots"]:
                    continue

                module_entries = []
                total_synergy = 0
                for module_type, coord in placements:
                    module_synergy = score_module(
                        module_type,
                        coord,
                        dome,
                        placements,
                        markers_by_coord,
                    )
                    module_entries.append(
                        {
                            "type": module_type,
                            "coord": [coord[0], coord[1]],
                            "synergy": module_synergy,
                        }
                    )
                    total_synergy += module_synergy

                module_entries.sort(key=lambda entry: (TYPE_ORDER[entry["type"]], entry["coord"]))
                tiebreak = (
                    dome,
                    tuple((entry["type"], tuple(entry["coord"])) for entry in module_entries),
                )

                if total_synergy > best_total or (
                    total_synergy == best_total and (best_tiebreak is None or tiebreak < best_tiebreak)
                ):
                    best_total = total_synergy
                    best_tiebreak = tiebreak
                    best_plan = {
                        "command_dome": [dome[0], dome[1]],
                        "modules": module_entries,
                        "population_used": population_used,
                        "total_synergy": total_synergy,
                    }

if best_plan is None:
    raise SystemExit("No valid plan found for scenario.")

output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(best_plan, f, indent=2)

print(f"Wrote optimal plan to {output_path} with total_synergy={best_plan['total_synergy']}")
PY
