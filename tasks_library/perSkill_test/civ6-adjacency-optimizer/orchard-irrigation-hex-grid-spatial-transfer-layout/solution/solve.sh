#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from itertools import combinations
from pathlib import Path


DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
INPUT_PATH = DATA_DIR / "orchard_plan.json"
OUTPUT_PATH = OUTPUT_DIR / "irrigation_layout.json"


def offset_to_cube(col, row):
    cube_x = col - (row - (row & 1)) // 2
    cube_z = row
    cube_y = -cube_x - cube_z
    return cube_x, cube_y, cube_z


def hex_distance(a, b):
    ax, ay, az = offset_to_cube(*a)
    bx, by, bz = offset_to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


scenario = json.loads(INPUT_PATH.read_text())
radius = scenario["irrigation_radius"]
conflict_distance = scenario["base_exclusion_distance"]

crops = scenario["crops"]
bases = scenario["candidate_bases"]
base_by_id = {item["id"]: item for item in bases}
sorted_base_ids = sorted(base_by_id)

coverage = {}
for base_id in sorted_base_ids:
    base = base_by_id[base_id]
    base_coord = (base["x"], base["y"])
    coverage[base_id] = sorted(
        crop["id"]
        for crop in crops
        if hex_distance(base_coord, (crop["x"], crop["y"])) <= radius
    )


def is_valid_selection(base_ids):
    for left, right in combinations(base_ids, 2):
        left_coord = (base_by_id[left]["x"], base_by_id[left]["y"])
        right_coord = (base_by_id[right]["x"], base_by_id[right]["y"])
        if hex_distance(left_coord, right_coord) <= conflict_distance:
            return False
    return True


selected = None
for size in range(1, len(sorted_base_ids) + 1):
    for candidate in combinations(sorted_base_ids, size):
        if not is_valid_selection(candidate):
            continue
        covered = set()
        for base_id in candidate:
            covered.update(coverage[base_id])
        if len(covered) == len(crops):
            selected = list(candidate)
            break
    if selected is not None:
        break

if selected is None:
    raise RuntimeError("No feasible irrigation layout found")

output = {
    "selected_bases": [
        {
            "base_id": base_id,
            "x": base_by_id[base_id]["x"],
            "y": base_by_id[base_id]["y"],
        }
        for base_id in selected
    ],
    "base_coverages": [
        {
            "base_id": base_id,
            "covers": coverage[base_id],
        }
        for base_id in selected
    ],
    "crop_coverages": [
        {
            "crop_id": crop["id"],
            "covered_by": [
                base_id
                for base_id in selected
                if crop["id"] in coverage[base_id]
            ],
        }
        for crop in crops
    ],
    "total_devices": len(selected),
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n")
PY
