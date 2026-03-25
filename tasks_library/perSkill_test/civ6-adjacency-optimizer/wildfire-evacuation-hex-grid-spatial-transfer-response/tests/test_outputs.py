import json
import os
from collections import deque
from pathlib import Path


import pytest


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
    assert rows, "terrain_map.txt 不能为空"
    width = len(rows[0])
    assert all(len(row) == width for row in rows), "terrain_map.txt 必须是等宽网格"
    height = len(rows)
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
        for next_coord in neighbors(x, y):
            if terrain.get(next_coord) not in BURNABLE:
                continue
            arrival = turn + 1
            current = fire[next_coord]
            if current is None or arrival < current:
                fire[next_coord] = arrival
                queue.append((next_coord, arrival))
    return fire


def expected_fire_rows(width, height, fire):
    rows = []
    for top_index in range(height):
        y = height - 1 - top_index
        rows.append([fire[(x, y)] for x in range(width)])
    return rows


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


@pytest.fixture(scope="session")
def incidents():
    return json.loads(INCIDENTS_PATH.read_text())


@pytest.fixture(scope="session")
def map_data():
    return load_map()


@pytest.fixture(scope="session")
def expected(map_data, incidents):
    _, width, height, terrain = map_data
    fire = compute_fire(terrain, incidents["ignitions"])
    shelters_by_coord = shelter_lookup(incidents["shelters"])
    routes = []
    for village in incidents["villages"]:
        route = best_route((village["x"], village["y"]), terrain, fire, shelters_by_coord)
        if route is None:
            routes.append(
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
            routes.append(route)
    return {
        "fire_arrival_turns": expected_fire_rows(width, height, fire),
        "village_routes": routes,
        "overall_evacuation_feasible": all(item["feasible"] for item in routes),
        "terrain": terrain,
        "fire": fire,
        "shelters_by_coord": shelters_by_coord,
    }


@pytest.fixture(scope="session")
def output():
    return json.loads(OUTPUT_PATH.read_text())


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"缺少输出文件: {OUTPUT_PATH}"


def test_top_level_schema(output):
    assert set(output.keys()) == {
        "fire_arrival_turns",
        "village_routes",
        "overall_evacuation_feasible",
    }
    assert isinstance(output["overall_evacuation_feasible"], bool)


def test_fire_arrival_matrix(output, expected, map_data):
    _, width, height, _ = map_data
    matrix = output["fire_arrival_turns"]
    assert isinstance(matrix, list)
    assert len(matrix) == height
    for row in matrix:
        assert isinstance(row, list)
        assert len(row) == width
        for value in row:
            assert value is None or isinstance(value, int)
    assert matrix == expected["fire_arrival_turns"]


def test_village_routes_schema(output, incidents):
    routes = output["village_routes"]
    assert isinstance(routes, list)
    assert len(routes) == len(incidents["villages"])
    expected_ids = [item["id"] for item in incidents["villages"]]
    actual_ids = [item["village_id"] for item in routes]
    assert actual_ids == expected_ids

    for route in routes:
        assert set(route.keys()) == {
            "village_id",
            "feasible",
            "chosen_shelter",
            "travel_turns",
            "path",
        }
        assert isinstance(route["feasible"], bool)
        assert isinstance(route["path"], list)
        if route["feasible"]:
            assert isinstance(route["chosen_shelter"], str)
            assert isinstance(route["travel_turns"], int)
            assert len(route["path"]) == route["travel_turns"] + 1
        else:
            assert route["chosen_shelter"] is None
            assert route["travel_turns"] is None
            assert route["path"] == []


def test_routes_are_semantically_valid(output, incidents, expected):
    terrain = expected["terrain"]
    fire = expected["fire"]
    shelters = set(expected["shelters_by_coord"])
    village_starts = {item["id"]: (item["x"], item["y"]) for item in incidents["villages"]}

    for route in output["village_routes"]:
        start = village_starts[route["village_id"]]
        if not route["feasible"]:
            continue

        assert tuple(route["path"][0]) == start
        assert tuple(route["path"][-1]) in shelters
        for index, point in enumerate(route["path"]):
            coord = tuple(point)
            assert terrain.get(coord) in PASSABLE
            if index > 0:
                previous = tuple(route["path"][index - 1])
                assert coord in neighbors(*previous)
            fire_turn = fire[coord]
            if fire_turn is not None:
                assert index < fire_turn


def test_expected_routes_and_global_feasibility(output, expected):
    assert output["village_routes"] == expected["village_routes"]
    assert output["overall_evacuation_feasible"] == expected["overall_evacuation_feasible"]
