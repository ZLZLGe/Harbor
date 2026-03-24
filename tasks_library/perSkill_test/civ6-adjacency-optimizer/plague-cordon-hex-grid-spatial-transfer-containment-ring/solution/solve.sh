#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from itertools import product
from pathlib import Path


def get_neighbors(x, y):
    if y % 2 == 0:
        directions = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
    else:
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]
    return [(x + dx, y + dy) for dx, dy in directions]


def hex_distance(a, b):
    x1, y1 = a
    x2, y2 = b

    def offset_to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    cx1, cy1, cz1 = offset_to_cube(x1, y1)
    cx2, cy2, cz2 = offset_to_cube(x2, y2)
    return (abs(cx1 - cx2) + abs(cy1 - cy2) + abs(cz1 - cz2)) // 2


def simulate_plan(scenario, towers, blocks):
    passable = {tuple(tile) for tile in scenario["tiles"]}
    sources = {tuple(tile) for tile in scenario["source_tiles"]}
    breach_tiles = {tuple(tile) for tile in scenario["breach_tiles"]}
    tower_specs = {tuple(entry["coord"]): entry for entry in scenario["tower_candidates"]}
    time_limit = scenario["time_limit"]

    infected = set(sources)
    frontier = set(sources)
    last_spread_turn = 0

    for turn in range(1, time_limit + 2):
        active_towers = []
        for tower in towers:
            spec = tower_specs[tower]
            if spec["activation_turn"] <= turn:
                active_towers.append((tower, spec["radius"]))

        new_tiles = set()
        for tile in frontier:
            for neighbor in get_neighbors(*tile):
                if neighbor not in passable or neighbor in infected or neighbor in blocks:
                    continue
                if any(hex_distance(neighbor, center) <= radius for center, radius in active_towers):
                    continue
                new_tiles.add(neighbor)

        if new_tiles:
            infected.update(new_tiles)
            frontier = new_tiles
            last_spread_turn = turn
        else:
            frontier = set()

        if infected & breach_tiles:
            return {
                "valid": False,
                "last_spread_turn": last_spread_turn,
            }

        if turn == time_limit + 1:
            return {
                "valid": not new_tiles,
                "last_spread_turn": last_spread_turn,
            }

    raise RuntimeError("Simulation fell through unexpectedly")


def canonical_coords(coords):
    return [list(coord) for coord in sorted(coords)]


scenario_path = Path(os.environ.get("SCENARIO_PATH", "/data/containment_ring/scenario.json"))
output_dir = Path(os.environ.get("OUTPUT_DIR", "/output"))
output_path = output_dir / "containment_ring.json"

with scenario_path.open() as f:
    scenario = json.load(f)

tower_specs = {tuple(entry["coord"]): entry for entry in scenario["tower_candidates"]}
block_specs = {tuple(entry["coord"]): entry for entry in scenario["block_candidates"]}
tower_coords = sorted(tower_specs)
block_coords = sorted(block_specs)

best = None
for tower_mask in range(1 << len(tower_coords)):
    chosen_towers = {
        tower_coords[index]
        for index in range(len(tower_coords))
        if tower_mask & (1 << index)
    }
    for block_mask in range(1 << len(block_coords)):
        chosen_blocks = {
            block_coords[index]
            for index in range(len(block_coords))
            if block_mask & (1 << index)
        }

        result = simulate_plan(scenario, chosen_towers, chosen_blocks)
        if not result["valid"]:
            continue

        total_cost = sum(tower_specs[coord]["cost"] for coord in chosen_towers)
        total_cost += sum(block_specs[coord]["cost"] for coord in chosen_blocks)

        candidate = (
            total_cost,
            result["last_spread_turn"],
            len(chosen_towers) + len(chosen_blocks),
            tuple(sorted(chosen_towers)),
            tuple(sorted(chosen_blocks)),
        )
        if best is None or candidate < best:
            best = candidate

if best is None:
    raise RuntimeError("No valid containment plan found")

solution = {
    "isolation_towers": canonical_coords(best[3]),
    "block_nodes": canonical_coords(best[4]),
    "total_cost": best[0],
    "last_spread_turn": best[1],
}

output_dir.mkdir(parents=True, exist_ok=True)
with output_path.open("w") as f:
    json.dump(solution, f, indent=2)

print(f"Wrote optimal containment plan to {output_path}")
print(json.dumps(solution, indent=2))
PY
