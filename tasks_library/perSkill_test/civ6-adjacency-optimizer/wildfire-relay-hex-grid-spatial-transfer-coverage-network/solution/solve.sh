#!/bin/bash

python3 <<'PY'
import json
from collections import deque
from itertools import combinations
from pathlib import Path


SCENARIO_PATH = Path("/data/wildfire_relay/scenario.json")
OUTPUT_PATH = Path("/output/wildfire_relay_plan.json")


def hex_distance(x1, y1, x2, y2):
    def offset_to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    a = offset_to_cube(x1, y1)
    b = offset_to_cube(x2, y2)
    return sum(abs(a[i] - b[i]) for i in range(3)) // 2


def is_connected(base, stations, link_radius):
    nodes = [base, *stations]
    seen = {base}
    queue = deque([base])

    while queue:
        current = queue.popleft()
        for nxt in nodes:
            if nxt in seen or nxt == current:
                continue
            if hex_distance(*current, *nxt) <= link_radius:
                seen.add(nxt)
                queue.append(nxt)

    return len(seen) == len(nodes)


def covered_hotspots(base, stations, hotspots, coverage_radius):
    nodes = [base, *stations]
    covered = []
    for hotspot in hotspots:
        coord = (hotspot["x"], hotspot["y"])
        if any(hex_distance(*coord, *node) <= coverage_radius for node in nodes):
            covered.append(coord)
    covered.sort()
    return covered


with SCENARIO_PATH.open() as f:
    scenario = json.load(f)

base = tuple(scenario["base"])
max_stations = scenario["max_stations"]
min_station_distance = scenario["min_station_distance"]
link_radius = scenario["link_radius"]
coverage_radius = scenario["coverage_radius"]

buildable_tiles = sorted(
    (tile["x"], tile["y"])
    for tile in scenario["tiles"]
    if tile.get("buildable") and (tile["x"], tile["y"]) != base
)
hotspots = scenario["hotspots"]
risk_lookup = {(h["x"], h["y"]): h["risk"] for h in hotspots}

best_score = -1
best_stations = []
best_covered = []

for count in range(max_stations + 1):
    for combo in combinations(buildable_tiles, count):
        if any(
            hex_distance(*left, *right) < min_station_distance
            for left, right in combinations(combo, 2)
        ):
            continue
        if not is_connected(base, combo, link_radius):
            continue

        covered = covered_hotspots(base, combo, hotspots, coverage_radius)
        score = sum(risk_lookup[coord] for coord in covered)

        if score > best_score:
            best_score = score
            best_stations = list(combo)
            best_covered = covered

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w") as f:
    json.dump(
        {
            "stations": [list(coord) for coord in best_stations],
            "covered_hotspots": [list(coord) for coord in best_covered],
            "coverage_score": best_score,
        },
        f,
        indent=2,
    )
PY
