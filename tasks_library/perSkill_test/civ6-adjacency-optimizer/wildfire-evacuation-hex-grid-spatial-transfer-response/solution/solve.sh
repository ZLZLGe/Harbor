#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
from collections import deque
from pathlib import Path


DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
MAP_PATH = DATA_DIR / "terrain_map.txt"
INCIDENTS_PATH = DATA_DIR / "incidents.json"
OUTPUT_PATH = OUTPUT_DIR / "wildfire_response.json"

PASSABLE = {".", "f", "s"}
BURNABLE = {".", "f"}


def neighbors(x, y):
    if y % 2 == 0:
        directions = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
    else:
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]
    return [(x + dx, y + dy) for dx, dy in directions]


def load_map():
    rows = [line.strip() for line in MAP_PATH.read_text().splitlines() if line.strip()]
    height = len(rows)
    width = len(rows[0])
    terrain = {}
    for top_index, row in enumerate(rows):
        y = height - 1 - top_index
        for x, char in enumerate(row):
            terrain[(x, y)] = char
    return rows, width, height, terrain


def compute_fire(terrain, ignitions):
    fire = {coord: None for coord in terrain}
    queue = deque()
    for item in ignitions:
        coord = (item["x"], item["y"])
        turn = item["turn"]
        if terrain.get(coord) not in BURNABLE:
            continue
        current = fire[coord]
        if current is None or turn < current:
            fire[coord] = turn
            queue.append((coord, turn))

    while queue:
        (x, y), turn = queue.popleft()
        for nx, ny in neighbors(x, y):
            coord = (nx, ny)
            if terrain.get(coord) not in BURNABLE:
                continue
            arrival = turn + 1
            current = fire[coord]
            if current is None or arrival < current:
                fire[coord] = arrival
                queue.append((coord, arrival))
    return fire


def shelter_lookup(shelters):
    return {(item["x"], item["y"]): item["id"] for item in shelters}


def best_route(start, terrain, fire, shelters_by_coord):
    start_fire = fire.get(start)
    if start_fire is not None and start_fire <= 0:
        return None

    queue = deque([(start, 0, [start])])
    best_steps = {start: 0}
    found_routes = []
    best_travel_turns = None

    while queue:
        position, turns, path = queue.popleft()
        if best_travel_turns is not None and turns > best_travel_turns:
            continue
        if position in shelters_by_coord:
            best_travel_turns = turns
            found_routes.append((turns, shelters_by_coord[position], path))
            continue

        for next_coord in neighbors(*position):
            if terrain.get(next_coord) not in PASSABLE:
                continue
            next_turn = turns + 1
            fire_turn = fire.get(next_coord)
            if fire_turn is not None and next_turn >= fire_turn:
                continue
            known = best_steps.get(next_coord)
            if known is not None and next_turn > known:
                continue
            best_steps[next_coord] = next_turn
            queue.append((next_coord, next_turn, path + [next_coord]))

    if not found_routes:
        return None

    found_routes.sort(key=lambda item: (item[0], item[1], [[x, y] for x, y in item[2]]))
    turns, shelter_id, path = found_routes[0]
    return {
        "feasible": True,
        "chosen_shelter": shelter_id,
        "travel_turns": turns,
        "path": [[x, y] for x, y in path],
    }


rows, width, height, terrain = load_map()
incidents = json.loads(INCIDENTS_PATH.read_text())
fire = compute_fire(terrain, incidents["ignitions"])
shelters_by_coord = shelter_lookup(incidents["shelters"])

fire_rows = []
for top_index in range(height):
    y = height - 1 - top_index
    fire_rows.append([fire[(x, y)] for x in range(width)])

village_routes = []
for village in incidents["villages"]:
    coord = (village["x"], village["y"])
    route = best_route(coord, terrain, fire, shelters_by_coord)
    if route is None:
        village_routes.append(
            {
                "village_id": village["id"],
                "feasible": False,
                "chosen_shelter": None,
                "travel_turns": None,
                "path": [],
            }
        )
    else:
        route["village_id"] = village["id"]
        village_routes.append(route)

result = {
    "fire_arrival_turns": fire_rows,
    "village_routes": village_routes,
    "overall_evacuation_feasible": all(item["feasible"] for item in village_routes),
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
PY
