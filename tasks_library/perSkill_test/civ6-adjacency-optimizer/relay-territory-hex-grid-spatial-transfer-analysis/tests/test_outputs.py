import csv
import json
import os
from collections import defaultdict
from pathlib import Path

import pytest


DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/output"))
CELLS_PATH = DATA_DIR / "relay_cells.csv"
ASSETS_PATH = DATA_DIR / "network_assets.json"
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
    rows = []
    with CELLS_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "x": int(row["x"]),
                    "y": int(row["y"]),
                    "cell_type": row["cell_type"],
                }
            )
    return rows


def compute_expected(cells, assets):
    service_cells = [(row["x"], row["y"]) for row in cells if row["cell_type"] == "service"]
    shadow_cells = {(row["x"], row["y"]) for row in cells if row["cell_type"] == "shadow"}
    stations = assets["base_stations"]

    territories = defaultdict(list)
    disputed = []
    for coord in service_cells:
        distances = {
            station["id"]: hex_distance(coord, (station["x"], station["y"]))
            for station in stations
        }
        best_distance = min(distances.values())
        nearest_station_ids = sorted(
            station_id
            for station_id, distance in distances.items()
            if distance == best_distance
        )
        if len(nearest_station_ids) == 1:
            territories[nearest_station_ids[0]].append([coord[0], coord[1]])
        else:
            disputed.append(
                {
                    "x": coord[0],
                    "y": coord[1],
                    "nearest_station_ids": nearest_station_ids,
                    "distance": best_distance,
                }
            )

    for cells_for_station in territories.values():
        cells_for_station.sort()
    disputed.sort(key=lambda item: (item["x"], item["y"]))

    assignments = []
    for checkpoint in assets["inspection_points"]:
        coord = (checkpoint["x"], checkpoint["y"])
        distances = {
            station["id"]: hex_distance(coord, (station["x"], station["y"]))
            for station in stations
        }
        best_distance = min(distances.values())
        nearest_station_ids = sorted(
            station_id
            for station_id, distance in distances.items()
            if distance == best_distance
        )
        assert len(nearest_station_ids) == 1, "题目数据要求巡检点唯一归属"
        assignments.append(
            {
                "checkpoint_id": checkpoint["id"],
                "assigned_station_id": nearest_station_ids[0],
                "distance": best_distance,
            }
        )

    expected = {
        "station_territories": [
            {
                "station_id": station["id"],
                "service_area_size": len(territories[station["id"]]),
                "cells": territories[station["id"]],
            }
            for station in stations
        ],
        "disputed_cells": disputed,
        "inspection_assignments": assignments,
    }
    return expected, set(service_cells), shadow_cells


@pytest.fixture(scope="session")
def cells():
    return load_cells()


@pytest.fixture(scope="session")
def assets():
    return json.loads(ASSETS_PATH.read_text())


@pytest.fixture(scope="session")
def expected_bundle(cells, assets):
    return compute_expected(cells, assets)


@pytest.fixture(scope="session")
def output():
    return json.loads(OUTPUT_PATH.read_text())


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"缺少输出文件: {OUTPUT_PATH}"


def test_top_level_schema(output):
    assert set(output.keys()) == {
        "station_territories",
        "disputed_cells",
        "inspection_assignments",
    }
    assert isinstance(output["station_territories"], list)
    assert isinstance(output["disputed_cells"], list)
    assert isinstance(output["inspection_assignments"], list)


def test_station_territories_schema_and_order(output, assets):
    stations = assets["base_stations"]
    territories = output["station_territories"]
    assert len(territories) == len(stations)
    assert [item["station_id"] for item in territories] == [station["id"] for station in stations]

    for item in territories:
        assert set(item.keys()) == {"station_id", "service_area_size", "cells"}
        assert isinstance(item["service_area_size"], int)
        assert isinstance(item["cells"], list)
        assert item["cells"] == sorted(item["cells"])
        for cell in item["cells"]:
            assert isinstance(cell, list)
            assert len(cell) == 2
            assert all(isinstance(value, int) for value in cell)
        assert item["service_area_size"] == len(item["cells"])


def test_disputed_cells_schema(output):
    disputed = output["disputed_cells"]
    assert disputed == sorted(disputed, key=lambda item: (item["x"], item["y"]))
    for item in disputed:
        assert set(item.keys()) == {"x", "y", "nearest_station_ids", "distance"}
        assert isinstance(item["x"], int)
        assert isinstance(item["y"], int)
        assert isinstance(item["distance"], int)
        assert isinstance(item["nearest_station_ids"], list)
        assert len(item["nearest_station_ids"]) >= 2
        assert item["nearest_station_ids"] == sorted(item["nearest_station_ids"])


def test_inspection_assignments_schema_and_order(output, assets):
    checkpoints = assets["inspection_points"]
    assignments = output["inspection_assignments"]
    assert len(assignments) == len(checkpoints)
    assert [item["checkpoint_id"] for item in assignments] == [point["id"] for point in checkpoints]
    for item in assignments:
        assert set(item.keys()) == {"checkpoint_id", "assigned_station_id", "distance"}
        assert isinstance(item["assigned_station_id"], str)
        assert isinstance(item["distance"], int)


def test_output_matches_expected_geometry(output, expected_bundle):
    expected, _, _ = expected_bundle
    assert output == expected


def test_service_cells_partition_is_complete(output, expected_bundle):
    _, service_cells, shadow_cells = expected_bundle
    assigned_cells = set()
    for territory in output["station_territories"]:
        for cell in territory["cells"]:
            coord = tuple(cell)
            assert coord in service_cells
            assert coord not in shadow_cells
            assert coord not in assigned_cells
            assigned_cells.add(coord)

    disputed_cells = {(item["x"], item["y"]) for item in output["disputed_cells"]}
    assert not (assigned_cells & disputed_cells)
    assert assigned_cells | disputed_cells == service_cells


def test_disputed_cells_are_true_ties(output, assets):
    stations = assets["base_stations"]
    for item in output["disputed_cells"]:
        coord = (item["x"], item["y"])
        distances = {
            station["id"]: hex_distance(coord, (station["x"], station["y"]))
            for station in stations
        }
        best_distance = min(distances.values())
        nearest_station_ids = sorted(
            station_id
            for station_id, distance in distances.items()
            if distance == best_distance
        )
        assert item["distance"] == best_distance
        assert item["nearest_station_ids"] == nearest_station_ids
