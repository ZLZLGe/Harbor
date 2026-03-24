#!/bin/bash

python3 <<'PY'
import json
from itertools import combinations
from pathlib import Path


TASK_ROOT_CANDIDATES = [
    Path.cwd(),
    Path.cwd().parent,
]

SCENARIO_PATH = Path("/data/warehouse_layout_scenario.json")
if not SCENARIO_PATH.exists():
    for candidate in TASK_ROOT_CANDIDATES:
        local_path = candidate / "environment/data/warehouse_layout_scenario.json"
        if local_path.exists():
            SCENARIO_PATH = local_path
            break

OUTPUT_PATH = Path("/output/warehouse_service_layout.json")
if not OUTPUT_PATH.parent.exists():
    for candidate in TASK_ROOT_CANDIDATES:
        fallback_dir = candidate / ".tmp_output"
        if fallback_dir.exists():
            OUTPUT_PATH = fallback_dir / "warehouse_service_layout.json"
            break


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def parse_layout(layout):
    fire_aisles = set()
    service_pads = []
    for y, row in enumerate(layout):
        for x, cell in enumerate(row):
            if cell == "F":
                fire_aisles.add((x, y))
            elif cell == "P":
                service_pads.append((x, y))
    return fire_aisles, service_pads


def score_for_distance(rule, demand, distance):
    return demand * rule["distance_scores"].get(str(distance), 0)


def best_device_entry(device_type, candidates, shelf, scenario):
    rule = scenario["service_rules"][device_type]
    demand = shelf[rule["demand_field"]]

    best_score = 0
    best_coord = None
    best_distance = None

    for coord in candidates:
        distance = manhattan(tuple(shelf["coord"]), coord)
        score = score_for_distance(rule, demand, distance)
        if score == 0:
            continue
        candidate_key = (score, -distance, -coord[1], -coord[0])
        best_key = (
            best_score,
            -(best_distance if best_distance is not None else 10**9),
            -(best_coord[1] if best_coord is not None else 10**9),
            -(best_coord[0] if best_coord is not None else 10**9),
        )
        if candidate_key > best_key:
            best_score = score
            best_coord = coord
            best_distance = distance

    return {
        "coord": list(best_coord) if best_coord is not None else None,
        "distance": best_distance,
        "score": best_score,
    }


def evaluate_layout(pick_stations, charging_dock, buffer_tables, scenario):
    shelf_service = {}
    total = 0
    for shelf in scenario["shelves"]:
        pick_entry = best_device_entry("pick_station", pick_stations, shelf, scenario)
        charge_entry = best_device_entry("charging_dock", [charging_dock], shelf, scenario)
        buffer_entry = best_device_entry("buffer_table", buffer_tables, shelf, scenario)
        shelf_total = pick_entry["score"] + charge_entry["score"] + buffer_entry["score"]
        shelf_service[shelf["id"]] = {
            "pick_station": pick_entry,
            "charging_dock": charge_entry,
            "buffer_table": buffer_entry,
            "total": shelf_total,
        }
        total += shelf_total
    return shelf_service, total


def is_legal_placement(coords, fire_aisles, scenario):
    if len(set(coords)) != len(coords):
        return False
    for coord in coords:
        if any(manhattan(coord, fire_cell) <= scenario["fire_clearance_distance"] for fire_cell in fire_aisles):
            return False
    for index, coord in enumerate(coords):
        for other in coords[index + 1:]:
            if manhattan(coord, other) < scenario["min_device_spacing"]:
                return False
    return True


with SCENARIO_PATH.open() as f:
    scenario = json.load(f)

fire_aisles, service_pads = parse_layout(scenario["layout"])
valid_pads = [
    pad
    for pad in service_pads
    if all(manhattan(pad, fire_cell) > scenario["fire_clearance_distance"] for fire_cell in fire_aisles)
]

best_total = -1
best_solution = None

for pick_stations in combinations(valid_pads, scenario["device_counts"]["pick_station"]):
    remaining_after_pick = [pad for pad in valid_pads if pad not in pick_stations]
    for charging_dock in remaining_after_pick:
        remaining_after_charge = [pad for pad in remaining_after_pick if pad != charging_dock]
        for buffer_tables in combinations(remaining_after_charge, scenario["device_counts"]["buffer_table"]):
            coords = list(pick_stations) + [charging_dock] + list(buffer_tables)
            if not is_legal_placement(coords, fire_aisles, scenario):
                continue
            shelf_service, total = evaluate_layout(pick_stations, charging_dock, buffer_tables, scenario)
            if total > best_total:
                best_total = total
                best_solution = {
                    "placements": {
                        "pick_stations": [list(coord) for coord in pick_stations],
                        "charging_dock": list(charging_dock),
                        "buffer_tables": [list(coord) for coord in buffer_tables],
                    },
                    "shelf_service": shelf_service,
                    "total_service_score": total,
                }

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w") as f:
    json.dump(best_solution, f, indent=2)

print(f"Wrote optimal layout to {OUTPUT_PATH} with total_service_score={best_total}")
PY
