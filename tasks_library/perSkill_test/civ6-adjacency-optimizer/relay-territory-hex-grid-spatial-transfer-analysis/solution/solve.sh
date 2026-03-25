#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
from collections import defaultdict
import os
from pathlib import Path


DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
OUTPUT_PATH = OUTPUT_DIR / "relay_territories.json"


def offset_to_cube(col, row):
    cube_x = col - (row - (row & 1)) // 2
    cube_z = row
    cube_y = -cube_x - cube_z
    return cube_x, cube_y, cube_z


def hex_distance(a, b):
    ax, ay, az = offset_to_cube(*a)
    bx, by, bz = offset_to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def load_cells():
    service_cells = []
    with (DATA_DIR / "relay_cells.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            coord = (int(row["x"]), int(row["y"]))
            if row["cell_type"] == "service":
                service_cells.append(coord)
    return service_cells


service_cells = load_cells()
assets = json.loads((DATA_DIR / "network_assets.json").read_text())
stations = assets["base_stations"]

territories = defaultdict(list)
disputed_cells = []
for coord in service_cells:
    distances = {
        station["id"]: hex_distance(coord, (station["x"], station["y"]))
        for station in stations
    }
    best_distance = min(distances.values())
    nearest_station_ids = sorted(
        station_id for station_id, distance in distances.items() if distance == best_distance
    )
    if len(nearest_station_ids) == 1:
        territories[nearest_station_ids[0]].append([coord[0], coord[1]])
    else:
        disputed_cells.append(
            {
                "x": coord[0],
                "y": coord[1],
                "nearest_station_ids": nearest_station_ids,
                "distance": best_distance,
            }
        )

for cells in territories.values():
    cells.sort()
disputed_cells.sort(key=lambda item: (item["x"], item["y"]))

inspection_assignments = []
for checkpoint in assets["inspection_points"]:
    coord = (checkpoint["x"], checkpoint["y"])
    distances = {
        station["id"]: hex_distance(coord, (station["x"], station["y"]))
        for station in stations
    }
    best_station_id, best_distance = min(distances.items(), key=lambda item: (item[1], item[0]))
    inspection_assignments.append(
        {
            "checkpoint_id": checkpoint["id"],
            "assigned_station_id": best_station_id,
            "distance": best_distance,
        }
    )

result = {
    "station_territories": [
        {
            "station_id": station["id"],
            "service_area_size": len(territories[station["id"]]),
            "cells": territories[station["id"]],
        }
        for station in stations
    ],
    "disputed_cells": disputed_cells,
    "inspection_assignments": inspection_assignments,
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(result, indent=2))
PY
