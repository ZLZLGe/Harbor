#!/usr/bin/env python3

import json
import os
from pathlib import Path

import pytest


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


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output"))
LOG_DIR = Path(os.environ.get("LOG_DIR", "/logs/verifier"))
SCENARIO_PATH = DATA_DIR / "containment_ring" / "scenario.json"
OUTPUT_PATH = OUTPUT_DIR / "containment_ring.json"
SCORE_FILE = LOG_DIR / "scores" / "containment_ring.txt"


def load_scenario():
    with SCENARIO_PATH.open() as f:
        return json.load(f)


def normalize_coord_list(items, field_name):
    assert isinstance(items, list), f"'{field_name}' must be a list"
    normalized = []
    seen = set()
    for index, coord in enumerate(items):
        assert isinstance(coord, list), f"{field_name}[{index}] must be a list"
        assert len(coord) == 2, f"{field_name}[{index}] must contain exactly 2 integers"
        assert all(isinstance(value, int) for value in coord), f"{field_name}[{index}] must contain integers"
        coord_tuple = tuple(coord)
        assert coord_tuple not in seen, f"Duplicate coordinate in '{field_name}': {coord}"
        seen.add(coord_tuple)
        normalized.append(coord_tuple)
    return normalized


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
                "breached_tiles": sorted(infected & breach_tiles),
                "contained": False,
            }

        if turn == time_limit + 1:
            return {
                "valid": not new_tiles,
                "last_spread_turn": last_spread_turn,
                "breached_tiles": [],
                "contained": not new_tiles,
            }

    raise RuntimeError("Simulation fell through unexpectedly")


def compute_optimal_cost(scenario):
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
            best = total_cost if best is None else min(best, total_cost)
    if best is None:
        raise AssertionError("Scenario has no valid containment plan")
    return best


@pytest.fixture(scope="session")
def scenario():
    return load_scenario()


@pytest.fixture(scope="session", autouse=True)
def ensure_score_dir():
    SCORE_FILE.parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def solution():
    assert OUTPUT_PATH.exists(), f"Solution file not found: {OUTPUT_PATH}"
    with OUTPUT_PATH.open() as f:
        data = json.load(f)
    assert isinstance(data, dict), "Solution must be a JSON object"
    return data


class TestFormat:
    def test_required_fields(self, solution):
        for field in ["isolation_towers", "block_nodes", "total_cost", "last_spread_turn"]:
            assert field in solution, f"Missing required field '{field}'"

    def test_coordinate_lists(self, solution):
        normalize_coord_list(solution["isolation_towers"], "isolation_towers")
        normalize_coord_list(solution["block_nodes"], "block_nodes")

    def test_numeric_fields(self, solution):
        assert isinstance(solution["total_cost"], int), "'total_cost' must be an integer"
        assert isinstance(solution["last_spread_turn"], int), "'last_spread_turn' must be an integer"
        assert solution["total_cost"] >= 0, "'total_cost' must be non-negative"
        assert solution["last_spread_turn"] >= 0, "'last_spread_turn' must be non-negative"


class TestEvaluation:
    def test_plan_validity_and_score(self, scenario, solution):
        tower_specs = {tuple(entry["coord"]): entry for entry in scenario["tower_candidates"]}
        block_specs = {tuple(entry["coord"]): entry for entry in scenario["block_candidates"]}

        towers = set(normalize_coord_list(solution["isolation_towers"], "isolation_towers"))
        blocks = set(normalize_coord_list(solution["block_nodes"], "block_nodes"))

        assert not (towers & blocks), "A coordinate cannot be both a tower and a block node"
        assert towers <= set(tower_specs), "All towers must come from tower_candidates"
        assert blocks <= set(block_specs), "All block nodes must come from block_candidates"

        expected_cost = sum(tower_specs[coord]["cost"] for coord in towers)
        expected_cost += sum(block_specs[coord]["cost"] for coord in blocks)
        assert solution["total_cost"] == expected_cost, "total_cost does not match selected defenses"

        result = simulate_plan(scenario, towers, blocks)
        assert result["valid"], (
            "Plan fails containment: "
            f"breached_tiles={result['breached_tiles']}, contained={result['contained']}"
        )
        assert solution["last_spread_turn"] == result["last_spread_turn"], (
            "last_spread_turn does not match the simulated final spread turn"
        )

        optimal_cost = compute_optimal_cost(scenario)
        score = min(1.0, optimal_cost / solution["total_cost"])
        SCORE_FILE.write_text(f"{score:.6f}")

        assert score > 0.0, "Valid plans must receive a positive score"
