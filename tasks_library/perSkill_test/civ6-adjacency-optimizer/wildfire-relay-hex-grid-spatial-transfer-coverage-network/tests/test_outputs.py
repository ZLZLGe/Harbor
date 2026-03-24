#!/usr/bin/env python3

import json
from collections import deque
from itertools import combinations
from pathlib import Path

import pytest


SCENARIO_PATH = Path("/data/wildfire_relay/scenario.json")
OUTPUT_PATH = Path("/output/wildfire_relay_plan.json")
SCORE_PATH = Path("/logs/verifier/scores/wildfire_relay.txt")


def hex_distance(x1, y1, x2, y2):
    def offset_to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    a = offset_to_cube(x1, y1)
    b = offset_to_cube(x2, y2)
    return sum(abs(a[i] - b[i]) for i in range(3)) // 2


def normalize_coord_list(items, field_name):
    if not isinstance(items, list):
        raise AssertionError(f"'{field_name}' must be a list")

    normalized = []
    for index, item in enumerate(items):
        assert isinstance(item, list), f"{field_name}[{index}] must be a list"
        assert len(item) == 2, f"{field_name}[{index}] must have exactly two coordinates"
        assert all(isinstance(value, int) for value in item), (
            f"{field_name}[{index}] coordinates must be integers"
        )
        normalized.append(tuple(item))

    return normalized


def load_scenario():
    with SCENARIO_PATH.open() as f:
        return json.load(f)


def load_solution():
    with OUTPUT_PATH.open() as f:
        return json.load(f)


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
    covered = set()
    for hotspot in hotspots:
        coord = (hotspot["x"], hotspot["y"])
        if any(hex_distance(*coord, *node) <= coverage_radius for node in nodes):
            covered.add(coord)
    return covered


def compute_optimal_score(scenario):
    base = tuple(scenario["base"])
    buildable_tiles = sorted(
        (tile["x"], tile["y"])
        for tile in scenario["tiles"]
        if tile.get("buildable") and (tile["x"], tile["y"]) != base
    )
    hotspots = scenario["hotspots"]
    risk_lookup = {(h["x"], h["y"]): h["risk"] for h in hotspots}

    best_score = 0
    for count in range(scenario["max_stations"] + 1):
        for combo in combinations(buildable_tiles, count):
            if any(
                hex_distance(*left, *right) < scenario["min_station_distance"]
                for left, right in combinations(combo, 2)
            ):
                continue
            if not is_connected(base, combo, scenario["link_radius"]):
                continue

            covered = covered_hotspots(base, combo, hotspots, scenario["coverage_radius"])
            score = sum(risk_lookup[coord] for coord in covered)
            best_score = max(best_score, score)

    return best_score


@pytest.fixture(scope="session")
def scenario():
    return load_scenario()


@pytest.fixture(scope="session")
def solution():
    if not OUTPUT_PATH.exists():
        pytest.fail(f"Solution file not found: {OUTPUT_PATH}")
    return load_solution()


class TestFormat:
    def test_solution_file_exists(self):
        assert OUTPUT_PATH.exists(), f"Solution file not found: {OUTPUT_PATH}"

    def test_solution_is_json_object(self, solution):
        assert isinstance(solution, dict), "Solution must be a JSON object"

    def test_required_fields_exist(self, solution):
        assert "stations" in solution, "Solution missing 'stations'"
        assert "covered_hotspots" in solution, "Solution missing 'covered_hotspots'"
        assert "coverage_score" in solution, "Solution missing 'coverage_score'"

    def test_field_types(self, solution):
        assert isinstance(solution["coverage_score"], int), "'coverage_score' must be an integer"
        normalize_coord_list(solution["stations"], "stations")
        normalize_coord_list(solution["covered_hotspots"], "covered_hotspots")


class TestEvaluation:
    def test_solution_validity_and_score(self, scenario, solution):
        SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)

        try:
            stations = normalize_coord_list(solution["stations"], "stations")
            claimed_covered = set(
                normalize_coord_list(solution["covered_hotspots"], "covered_hotspots")
            )
            assert len(stations) == len(set(stations)), "'stations' contains duplicates"
            assert len(claimed_covered) == len(solution["covered_hotspots"]), (
                "'covered_hotspots' contains duplicates"
            )

            base = tuple(scenario["base"])
            tiles = {(tile["x"], tile["y"]): tile for tile in scenario["tiles"]}
            hotspot_lookup = {(h["x"], h["y"]): h["risk"] for h in scenario["hotspots"]}

            assert len(stations) <= scenario["max_stations"], (
                f"Expected at most {scenario['max_stations']} stations"
            )

            for station in stations:
                assert station in tiles, f"Station {station} is outside the map"
                assert station != base, f"Station {station} overlaps the base"
                assert tiles[station].get("buildable") is True, (
                    f"Station {station} is not on a buildable tile"
                )

            for left, right in combinations(stations, 2):
                assert hex_distance(*left, *right) >= scenario["min_station_distance"], (
                    f"Stations {left} and {right} violate min_station_distance"
                )

            assert is_connected(base, stations, scenario["link_radius"]), (
                "Stations do not form a base-connected relay network"
            )

            for hotspot in claimed_covered:
                assert hotspot in hotspot_lookup, f"Unknown hotspot listed: {hotspot}"

            actual_covered = covered_hotspots(
                base, stations, scenario["hotspots"], scenario["coverage_radius"]
            )
            assert claimed_covered == actual_covered, (
                f"covered_hotspots mismatch: claimed {sorted(claimed_covered)}, "
                f"actual {sorted(actual_covered)}"
            )

            actual_score = sum(hotspot_lookup[coord] for coord in actual_covered)
            assert solution["coverage_score"] == actual_score, (
                f"coverage_score {solution['coverage_score']} != actual {actual_score}"
            )

            optimal_score = compute_optimal_score(scenario)
            score = actual_score / optimal_score if optimal_score else 0.0
            SCORE_PATH.write_text(str(score))

        except AssertionError:
            SCORE_PATH.write_text("0.0")
            raise
