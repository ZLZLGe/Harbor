#!/usr/bin/env python3

import json
import os
from itertools import combinations
from pathlib import Path

try:
    import pytest
except ImportError:  # pragma: no cover - fallback for non-pytest local validation
    class _PytestShim:
        @staticmethod
        def fixture(*_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    pytest = _PytestShim()


DIRECTIONS_EVEN_ROW = [
    (1, 0),
    (0, -1),
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
]

DIRECTIONS_ODD_ROW = [
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (0, 1),
    (1, 1),
]

TYPE_ORDER = {"RESEARCH": 0, "INDUSTRIAL": 1, "LIFE_SUPPORT": 2}

SCENARIO_PATH = Path(os.environ.get("SCENARIO_PATH", "/data/mars_scenario.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/output/mars_colony_plan.json"))
SCORE_DIR = Path(os.environ.get("SCORE_DIR", "/logs/verifier/scores"))


def get_neighbors(coord):
    x, y = coord
    directions = DIRECTIONS_ODD_ROW if y % 2 == 1 else DIRECTIONS_EVEN_ROW
    return [(x + dx, y + dy) for dx, dy in directions]


def hex_distance(a, b):
    def offset_to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    ax, ay, az = offset_to_cube(*a)
    bx, by, bz = offset_to_cube(*b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def load_scenario():
    with open(SCENARIO_PATH) as f:
        return json.load(f)


def load_solution():
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def build_context(scenario):
    tiles = {(tile["x"], tile["y"]): tile for tile in scenario["tiles"]}
    buildable = {
        coord: tile
        for coord, tile in tiles.items()
        if tile.get("buildable", False)
    }
    markers_by_coord = {
        coord: list(tile.get("markers", []))
        for coord, tile in tiles.items()
    }
    return tiles, buildable, markers_by_coord


def calculate_module_synergy(module_type, coord, dome, placements, markers_by_coord):
    adjacent = get_neighbors(coord)
    adjacent_markers = []
    for neighbor in adjacent:
        adjacent_markers.extend(markers_by_coord.get(neighbor, []))

    score = 0
    if dome in adjacent:
        score += 1

    if module_type == "RESEARCH":
        score += 2 * adjacent_markers.count("science_site")
        score += sum(
            1
            for other_type, other_coord in placements
            if other_type == "LIFE_SUPPORT" and other_coord in adjacent
        )
    elif module_type == "INDUSTRIAL":
        score += 2 * adjacent_markers.count("ore_field")
        score += adjacent_markers.count("power_node")
    elif module_type == "LIFE_SUPPORT":
        score += 2 * adjacent_markers.count("ice_vent")
        score += sum(
            1
            for other_type, other_coord in placements
            if other_type == "RESEARCH" and other_coord in adjacent
        )
    else:
        raise ValueError(f"Unknown module type: {module_type}")

    return score


def validate_solution(solution, scenario):
    errors = []
    tiles, buildable, markers_by_coord = build_context(scenario)

    if not isinstance(solution, dict):
        return {"valid": False, "errors": ["Solution must be a JSON object"], "score": 0.0}

    if "command_dome" not in solution:
        errors.append("Missing command_dome")
        return {"valid": False, "errors": errors, "score": 0.0}

    if "modules" not in solution:
        errors.append("Missing modules")
        return {"valid": False, "errors": errors, "score": 0.0}

    command_dome = solution["command_dome"]
    modules = solution["modules"]
    population_used = solution.get("population_used")
    total_synergy = solution.get("total_synergy")

    if not isinstance(command_dome, list) or len(command_dome) != 2:
        errors.append("command_dome must be [x, y]")
        return {"valid": False, "errors": errors, "score": 0.0}
    dome = tuple(command_dome)

    if dome not in buildable:
        errors.append(f"command_dome must be on a buildable tile: {dome}")
    else:
        allowed_command_terrains = set(scenario["terrain_rules"]["command_dome"])
        if buildable[dome]["terrain"] not in allowed_command_terrains:
            errors.append(f"command_dome terrain invalid at {dome}")

    if not isinstance(modules, list):
        errors.append("modules must be a list")
        return {"valid": False, "errors": errors, "score": 0.0}

    expected_count = sum(scenario["required_modules"].values())
    if len(modules) != expected_count:
        errors.append(f"Expected {expected_count} modules, got {len(modules)}")

    placements = []
    seen_positions = {dome}
    counts = {"RESEARCH": 0, "INDUSTRIAL": 0, "LIFE_SUPPORT": 0}

    for index, module in enumerate(modules):
        if not isinstance(module, dict):
            errors.append(f"modules[{index}] must be an object")
            continue

        module_type = module.get("type")
        coord = module.get("coord")
        synergy = module.get("synergy")

        if module_type not in counts:
            errors.append(f"modules[{index}] has unknown type {module_type}")
            continue
        counts[module_type] += 1

        if not isinstance(coord, list) or len(coord) != 2:
            errors.append(f"modules[{index}] coord must be [x, y]")
            continue
        coord_tuple = tuple(coord)

        if coord_tuple in seen_positions:
            errors.append(f"Duplicate placement at {coord_tuple}")
            continue
        seen_positions.add(coord_tuple)

        if coord_tuple not in buildable:
            errors.append(f"modules[{index}] must be on a buildable tile: {coord_tuple}")
            continue

        allowed_terrains = set(scenario["terrain_rules"][module_type])
        if buildable[coord_tuple]["terrain"] not in allowed_terrains:
            errors.append(
                f"{module_type} cannot be placed on {buildable[coord_tuple]['terrain']} at {coord_tuple}"
            )

        if hex_distance(dome, coord_tuple) > scenario["supply_radius"]:
            errors.append(f"{module_type} at {coord_tuple} is outside supply radius")

        if not isinstance(synergy, int):
            errors.append(f"modules[{index}] synergy must be an integer")
            continue

        placements.append((module_type, coord_tuple, synergy))

    for module_type, expected in scenario["required_modules"].items():
        if counts[module_type] != expected:
            errors.append(
                f"Expected {expected} {module_type} modules, got {counts[module_type]}"
            )

    industrial_positions = [coord for module_type, coord, _ in placements if module_type == "INDUSTRIAL"]
    life_positions = [coord for module_type, coord, _ in placements if module_type == "LIFE_SUPPORT"]
    for industrial in industrial_positions:
        adjacent = set(get_neighbors(industrial))
        for life in life_positions:
            if life in adjacent:
                errors.append(f"INDUSTRIAL at {industrial} cannot be adjacent to LIFE_SUPPORT at {life}")

    calculated_population = sum(
        scenario["module_costs"][module_type]
        for module_type, _, _ in placements
    )
    if population_used != calculated_population:
        errors.append(
            f"population_used {population_used} does not match calculated cost {calculated_population}"
        )
    if calculated_population > scenario["population_slots"]:
        errors.append(
            f"Population usage {calculated_population} exceeds limit {scenario['population_slots']}"
        )

    placement_pairs = [(module_type, coord) for module_type, coord, _ in placements]
    calculated_total = 0
    for module_type, coord, synergy in placements:
        expected_synergy = calculate_module_synergy(
            module_type,
            coord,
            dome,
            placement_pairs,
            markers_by_coord,
        )
        if synergy != expected_synergy:
            errors.append(
                f"{module_type} at {coord} reports synergy {synergy}, expected {expected_synergy}"
            )
        calculated_total += expected_synergy

    if total_synergy != calculated_total:
        errors.append(
            f"total_synergy {total_synergy} does not match calculated total {calculated_total}"
        )

    optimal_total, _ = compute_optimal_plan(scenario)
    valid = not errors
    score = (calculated_total / optimal_total) if valid else 0.0

    return {
        "valid": valid,
        "errors": errors,
        "calculated_total": calculated_total,
        "optimal_total": optimal_total,
        "score": score,
    }


def compute_optimal_plan(scenario):
    _, buildable, markers_by_coord = build_context(scenario)

    command_candidates = sorted(
        coord
        for coord, tile in buildable.items()
        if tile["terrain"] in scenario["terrain_rules"]["command_dome"]
    )

    best_total = -1
    best_tiebreak = None

    for dome in command_candidates:
        in_range = sorted(
            coord
            for coord in buildable
            if coord != dome and hex_distance(dome, coord) <= scenario["supply_radius"]
        )
        research_candidates = [
            coord
            for coord in in_range
            if buildable[coord]["terrain"] in scenario["terrain_rules"]["RESEARCH"]
        ]
        industrial_candidates = [
            coord
            for coord in in_range
            if buildable[coord]["terrain"] in scenario["terrain_rules"]["INDUSTRIAL"]
        ]
        life_candidates = [
            coord
            for coord in in_range
            if buildable[coord]["terrain"] in scenario["terrain_rules"]["LIFE_SUPPORT"]
        ]

        for research in research_candidates:
            for industrial in industrial_candidates:
                if industrial == research:
                    continue
                remaining_life = [
                    coord for coord in life_candidates if coord not in {research, industrial}
                ]
                for life_positions in combinations(remaining_life, 2):
                    if any(life in get_neighbors(industrial) for life in life_positions):
                        continue

                    placements = [
                        ("RESEARCH", research),
                        ("INDUSTRIAL", industrial),
                        ("LIFE_SUPPORT", life_positions[0]),
                        ("LIFE_SUPPORT", life_positions[1]),
                    ]
                    population_used = sum(
                        scenario["module_costs"][module_type]
                        for module_type, _ in placements
                    )
                    if population_used > scenario["population_slots"]:
                        continue

                    total = sum(
                        calculate_module_synergy(
                            module_type,
                            coord,
                            dome,
                            placements,
                            markers_by_coord,
                        )
                        for module_type, coord in placements
                    )
                    modules = [
                        {"type": module_type, "coord": [coord[0], coord[1]]}
                        for module_type, coord in placements
                    ]
                    modules.sort(key=lambda entry: (TYPE_ORDER[entry["type"]], entry["coord"]))
                    tiebreak = (
                        dome,
                        tuple((entry["type"], tuple(entry["coord"])) for entry in modules),
                    )
                    if total > best_total or (
                        total == best_total and (best_tiebreak is None or tiebreak < best_tiebreak)
                    ):
                        best_total = total
                        best_tiebreak = tiebreak

    return best_total, best_tiebreak


@pytest.fixture(scope="session", autouse=True)
def create_score_dir():
    SCORE_DIR.mkdir(parents=True, exist_ok=True)


class TestFormat:
    def test_solution_file_exists(self):
        assert OUTPUT_PATH.exists(), f"Solution file not found: {OUTPUT_PATH}"

    def test_solution_is_json_object(self):
        with open(OUTPUT_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict), "Solution must be a JSON object"

    def test_required_fields_exist(self):
        solution = load_solution()
        assert "command_dome" in solution, "Missing command_dome"
        assert "modules" in solution, "Missing modules"
        assert "population_used" in solution, "Missing population_used"
        assert "total_synergy" in solution, "Missing total_synergy"


class TestEvaluation:
    def test_solution_is_valid_and_scored(self):
        scenario = load_scenario()
        solution = load_solution()
        result = validate_solution(solution, scenario)
        (SCORE_DIR / "mars_colony_plan.txt").write_text(str(result["score"]))
        assert result["valid"], f"Invalid solution: {result['errors']}"


if __name__ == "__main__":
    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    scenario = load_scenario()
    solution = load_solution()
    result = validate_solution(solution, scenario)
    (SCORE_DIR / "mars_colony_plan.txt").write_text(str(result["score"]))
    if not result["valid"]:
        raise SystemExit("Invalid solution: " + "; ".join(result["errors"]))
    print(
        f"Valid solution. total={result['calculated_total']} optimal={result['optimal_total']} score={result['score']:.3f}"
    )
