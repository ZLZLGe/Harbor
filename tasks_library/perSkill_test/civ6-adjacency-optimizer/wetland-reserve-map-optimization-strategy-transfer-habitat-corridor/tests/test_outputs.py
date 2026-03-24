#!/usr/bin/env python3

import json
import os
from collections import deque
from itertools import combinations
from pathlib import Path

try:
    import pytest
except ImportError:  # pragma: no cover
    class _PytestShim:
        @staticmethod
        def fixture(*_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    pytest = _PytestShim()


SCENARIO_PATH = Path(os.environ.get("SCENARIO_PATH", "/data/wetland_reserve_scenario.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/output/wetland_corridor_plan.json"))
SCORE_DIR = Path(os.environ.get("SCORE_DIR", "/logs/verifier/scores"))


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def orthogonal_neighbors(coord):
    x, y = coord
    return [
        (x + 1, y),
        (x - 1, y),
        (x, y + 1),
        (x, y - 1),
    ]


class ScenarioModel:
    def __init__(self, scenario):
        self.scenario = scenario
        self.entry = tuple(scenario["entry"])
        self.corridor_cells = {tuple(coord) for coord in scenario["corridor_cells"]}
        self.sites = {
            tuple(site["coord"]): site
            for site in scenario["sites"]
        }
        self.open_sites = {
            coord: site
            for coord, site in self.sites.items()
            if not site.get("blocked", False)
        }
        self.zone_capacity_limits = scenario["zone_capacity_limits"]
        self.zone_capacity_costs = scenario["zone_capacity_costs"]
        self.coverage_radius = scenario["coverage_radius"]
        self.support_bonus_rules = scenario["support_bonus_rules"]
        self.network_bonus = scenario["network_bonus"]
        self.noise_penalty_weights = scenario["noise_penalty_weights"]
        self.habitat_patches = [
            {
                **patch,
                "coord": tuple(patch["coord"]),
            }
            for patch in scenario["habitat_patches"]
        ]
        self.reachable_corridors = self._compute_reachable_corridors()
        self.site_access = {
            coord: [
                neighbor
                for neighbor in orthogonal_neighbors(coord)
                if neighbor in self.reachable_corridors
            ]
            for coord in self.open_sites
        }
        self.site_distance_cache = {}
        self.patch_distance_cache = {}

    def _compute_reachable_corridors(self):
        queue = deque([self.entry])
        visited = {self.entry}
        while queue:
            current = queue.popleft()
            for neighbor in orthogonal_neighbors(current):
                if neighbor in self.corridor_cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def site_to_site_distance(self, site_a, site_b):
        key = tuple(sorted((site_a, site_b)))
        if key in self.site_distance_cache:
            return self.site_distance_cache[key]

        starts = self.site_access.get(site_a, [])
        targets = set(self.site_access.get(site_b, []))
        if not starts or not targets:
            self.site_distance_cache[key] = None
            return None

        best = None
        for start in starts:
            queue = deque([(start, 0)])
            visited = {start}
            while queue:
                current, distance = queue.popleft()
                if current in targets:
                    candidate = distance + 2
                    if best is None or candidate < best:
                        best = candidate
                    break
                for neighbor in orthogonal_neighbors(current):
                    if neighbor in self.reachable_corridors and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, distance + 1))

        self.site_distance_cache[key] = best
        return best

    def site_to_patch_distance(self, site_coord, patch_coord):
        key = (site_coord, patch_coord)
        if key in self.patch_distance_cache:
            return self.patch_distance_cache[key]

        starts = self.site_access.get(site_coord, [])
        if patch_coord not in self.reachable_corridors or not starts:
            self.patch_distance_cache[key] = None
            return None

        best = None
        for start in starts:
            queue = deque([(start, 0)])
            visited = {start}
            while queue:
                current, distance = queue.popleft()
                if current == patch_coord:
                    candidate = distance + 1
                    if best is None or candidate < best:
                        best = candidate
                    break
                for neighbor in orthogonal_neighbors(current):
                    if neighbor in self.reachable_corridors and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, distance + 1))

        self.patch_distance_cache[key] = best
        return best

    def is_network_connected(self, coords):
        coords = list(coords)
        if not coords:
            return False

        limit = self.network_bonus["max_link_distance"]
        seen = {coords[0]}
        stack = [coords[0]]
        while stack:
            current = stack.pop()
            for other in coords:
                if other in seen or other == current:
                    continue
                travel = self.site_to_site_distance(current, other)
                if travel is not None and travel <= limit:
                    seen.add(other)
                    stack.append(other)
        return len(seen) == len(coords)


def load_scenario():
    with open(SCENARIO_PATH) as f:
        return json.load(f)


def load_solution():
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def parse_coord(name, value, errors):
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, int) for v in value):
        errors.append(f"{name} must be [x, y] with integers")
        return None
    return tuple(value)


def evaluate_plan(solution, scenario, include_optimal=True, check_declared_fields=True):
    errors = []
    model = ScenarioModel(scenario)

    if not isinstance(solution, dict):
        return {"valid": False, "errors": ["Solution must be a JSON object"], "score": 0.0}

    required_keys = {
        "nest_boxes",
        "buffers",
        "monitoring_point",
        "zone_capacity_used",
        "score_breakdown",
    }
    for key in required_keys:
        if key not in solution:
            errors.append(f"Missing required key: {key}")
    if errors:
        return {"valid": False, "errors": errors, "score": 0.0}

    nest_boxes = solution["nest_boxes"]
    buffers = solution["buffers"]
    monitoring_point = solution["monitoring_point"]
    zone_capacity_used = solution["zone_capacity_used"]
    score_breakdown = solution["score_breakdown"]

    if not isinstance(nest_boxes, list) or len(nest_boxes) != scenario["required_counts"]["NEST_BOX"]:
        errors.append("nest_boxes must contain exactly two coordinates")
        nest_coords = []
    else:
        nest_coords = []
        for index, coord in enumerate(nest_boxes):
            parsed = parse_coord(f"nest_boxes[{index}]", coord, errors)
            if parsed is not None:
                nest_coords.append(parsed)

    if not isinstance(buffers, list) or len(buffers) != scenario["required_counts"]["BUFFER"]:
        errors.append("buffers must contain exactly two coordinates")
        buffer_coords = []
    else:
        buffer_coords = []
        for index, coord in enumerate(buffers):
            parsed = parse_coord(f"buffers[{index}]", coord, errors)
            if parsed is not None:
                buffer_coords.append(parsed)

    monitor_coord = parse_coord("monitoring_point", monitoring_point, errors)

    if not isinstance(zone_capacity_used, dict):
        errors.append("zone_capacity_used must be an object")
    if not isinstance(score_breakdown, dict):
        errors.append("score_breakdown must be an object")

    expected_score_keys = {
        "base_habitat",
        "coverage_bonus",
        "support_bonus",
        "network_bonus",
        "installation_cost",
        "noise_penalty",
        "total_score",
    }
    if isinstance(score_breakdown, dict):
        for key in expected_score_keys:
            if key not in score_breakdown:
                errors.append(f"score_breakdown missing {key}")
            elif not isinstance(score_breakdown[key], int):
                errors.append(f"score_breakdown.{key} must be an integer")

    if errors:
        return {"valid": False, "errors": errors, "score": 0.0}

    assignments = [
        ("NEST_BOX", nest_coords[0]),
        ("NEST_BOX", nest_coords[1]),
        ("BUFFER", buffer_coords[0]),
        ("BUFFER", buffer_coords[1]),
        ("MONITOR", monitor_coord),
    ]
    coords_only = [coord for _, coord in assignments]

    if len(set(coords_only)) != len(coords_only):
        errors.append("All facilities must occupy distinct coordinates")

    for role, coord in assignments:
        if coord not in model.open_sites:
            if coord in model.sites and model.sites[coord].get("blocked", False):
                errors.append(f"{role} uses blocked site {coord}")
            else:
                errors.append(f"{role} uses unknown or unavailable site {coord}")
            continue
        if not model.site_access.get(coord):
            errors.append(f"{role} uses unreachable site {coord}")

    if len(nest_coords) == 2 and manhattan(nest_coords[0], nest_coords[1]) < 4:
        errors.append("nest_boxes violate the minimum Manhattan spacing of 4")

    if monitor_coord is not None:
        for nest_coord in nest_coords:
            if manhattan(monitor_coord, nest_coord) < 3:
                errors.append("monitoring_point must be at least Manhattan distance 3 from every nest box")

    expected_zone_usage = {zone: 0 for zone in scenario["zone_capacity_limits"]}
    base_habitat = 0
    installation_cost = 0
    noise_penalty = 0

    for role, coord in assignments:
        site = model.open_sites.get(coord)
        if site is None:
            continue
        zone = site["zone"]
        expected_zone_usage[zone] += scenario["zone_capacity_costs"][role]
        if expected_zone_usage[zone] > scenario["zone_capacity_limits"][zone]:
            errors.append(
                f"Zone {zone} uses {expected_zone_usage[zone]} capacity, "
                f"exceeding limit {scenario['zone_capacity_limits'][zone]}"
            )
        metrics = site["role_metrics"][role]
        base_habitat += metrics["habitat_value"]
        installation_cost += metrics["installation_cost"]
        noise_penalty += site["noise_level"] * scenario["noise_penalty_weights"][role]

    if check_declared_fields:
        if set(zone_capacity_used.keys()) != set(expected_zone_usage.keys()):
            errors.append("zone_capacity_used must include exactly the scenario zones")
        else:
            for zone, expected in expected_zone_usage.items():
                actual = zone_capacity_used.get(zone)
                if not isinstance(actual, int):
                    errors.append(f"zone_capacity_used.{zone} must be an integer")
                elif actual != expected:
                    errors.append(f"zone_capacity_used.{zone}={actual}, expected {expected}")

    coverage_bonus = 0
    for patch in model.habitat_patches:
        patch_coord = patch["coord"]
        if any(
            (distance := model.site_to_patch_distance(nest_coord, patch_coord)) is not None
            and distance <= scenario["coverage_radius"]["NEST_BOX"]
            for nest_coord in nest_coords
        ):
            coverage_bonus += patch["nest_bonus"]

        if any(
            (distance := model.site_to_patch_distance(buffer_coord, patch_coord)) is not None
            and distance <= scenario["coverage_radius"]["BUFFER"]
            for buffer_coord in buffer_coords
        ):
            coverage_bonus += patch["buffer_bonus"]

        monitor_distance = model.site_to_patch_distance(monitor_coord, patch_coord)
        if monitor_distance is not None and monitor_distance <= scenario["coverage_radius"]["MONITOR"]:
            coverage_bonus += patch["monitor_bonus"]

    support_bonus = 0
    for rule in scenario["support_bonus_rules"]:
        if rule["source_role"] == "NEST_BOX":
            for nest_coord in nest_coords:
                if any(
                    (distance := model.site_to_site_distance(nest_coord, buffer_coord)) is not None
                    and distance <= rule["max_travel_distance"]
                    for buffer_coord in buffer_coords
                ):
                    support_bonus += rule["bonus"]
        elif rule["source_role"] == "MONITOR":
            if any(
                (distance := model.site_to_site_distance(monitor_coord, buffer_coord)) is not None
                and distance <= rule["max_travel_distance"]
                for buffer_coord in buffer_coords
            ):
                support_bonus += rule["bonus"]

    network_bonus = (
        scenario["network_bonus"]["bonus"]
        if model.is_network_connected(coords_only)
        else 0
    )
    total_score = (
        base_habitat
        + coverage_bonus
        + support_bonus
        + network_bonus
        - installation_cost
        - noise_penalty
    )

    expected_breakdown = {
        "base_habitat": base_habitat,
        "coverage_bonus": coverage_bonus,
        "support_bonus": support_bonus,
        "network_bonus": network_bonus,
        "installation_cost": installation_cost,
        "noise_penalty": noise_penalty,
        "total_score": total_score,
    }

    if check_declared_fields and isinstance(score_breakdown, dict):
        for key, expected in expected_breakdown.items():
            actual = score_breakdown.get(key)
            if actual != expected:
                errors.append(f"score_breakdown.{key}={actual}, expected {expected}")

    valid = not errors
    if include_optimal:
        optimal_total, _ = compute_optimal_plan(scenario)
        score = (total_score / optimal_total) if valid else 0.0
        if score > 1.0:
            score = 1.0
    else:
        optimal_total = None
        score = 0.0

    return {
        "valid": valid,
        "errors": errors,
        "score": score,
        "total_score": total_score,
        "optimal_score": optimal_total,
        "plan": expected_breakdown,
    }


def canonical_key(plan):
    score = plan["score_breakdown"]
    return (
        score["total_score"],
        score["coverage_bonus"],
        score["support_bonus"],
        -score["noise_penalty"],
        -score["installation_cost"],
        tuple(tuple(coord) for coord in plan["nest_boxes"]),
        tuple(tuple(coord) for coord in plan["buffers"]),
        tuple(plan["monitoring_point"]),
    )


def generate_plan(model, nests, buffers, monitor):
    plan = {
        "nest_boxes": [[nests[0][0], nests[0][1]], [nests[1][0], nests[1][1]]],
        "buffers": [[buffers[0][0], buffers[0][1]], [buffers[1][0], buffers[1][1]]],
        "monitoring_point": [monitor[0], monitor[1]],
    }
    result = evaluate_plan(
        {
            **plan,
            "zone_capacity_used": {zone: 0 for zone in model.zone_capacity_limits},
            "score_breakdown": {
                "base_habitat": 0,
                "coverage_bonus": 0,
                "support_bonus": 0,
                "network_bonus": 0,
                "installation_cost": 0,
                "noise_penalty": 0,
                "total_score": 0,
            },
        },
        model.scenario,
        include_optimal=False,
        check_declared_fields=False,
    )
    if not result["valid"]:
        return None

    full_plan = {
        **plan,
        "zone_capacity_used": {zone: 0 for zone in model.zone_capacity_limits},
        "score_breakdown": result["plan"],
    }

    for role, coord in [
        ("NEST_BOX", nests[0]),
        ("NEST_BOX", nests[1]),
        ("BUFFER", buffers[0]),
        ("BUFFER", buffers[1]),
        ("MONITOR", monitor),
    ]:
        zone = model.open_sites[coord]["zone"]
        full_plan["zone_capacity_used"][zone] += model.zone_capacity_costs[role]

    return full_plan


def compute_optimal_plan(scenario):
    model = ScenarioModel(scenario)
    open_coords = sorted(model.open_sites)
    best_total = None
    best_plan = None

    for nests in combinations(open_coords, 2):
        remaining_after_nests = [coord for coord in open_coords if coord not in nests]
        for buffers in combinations(remaining_after_nests, 2):
            remaining_after_buffers = [
                coord
                for coord in remaining_after_nests
                if coord not in buffers
            ]
            for monitor in remaining_after_buffers:
                plan = generate_plan(model, nests, buffers, monitor)
                if plan is None:
                    continue
                total = plan["score_breakdown"]["total_score"]
                if best_total is None or canonical_key(plan) > canonical_key(best_plan):
                    best_total = total
                    best_plan = plan

    return best_total, best_plan


@pytest.fixture(scope="session")
def scenario():
    return load_scenario()


@pytest.fixture(scope="session")
def solution():
    if not OUTPUT_PATH.exists():
        pytest.fail(f"Solution file not found: {OUTPUT_PATH}")
    return load_solution()


def test_solution_file_exists():
    assert OUTPUT_PATH.exists(), f"Solution file not found: {OUTPUT_PATH}"


def test_solution_is_valid_json():
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    assert isinstance(data, dict), "Solution must be a JSON object"


def test_solution_scores_and_constraints(scenario, solution):
    result = evaluate_plan(solution, scenario)

    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    (SCORE_DIR / "wetland_corridor_plan.txt").write_text(f"{result['score']:.6f}")

    assert result["valid"], f"Invalid wetland corridor plan: {result['errors']}"


def test_solution_is_optimal(scenario, solution):
    result = evaluate_plan(solution, scenario)
    optimal_total, optimal_plan = compute_optimal_plan(scenario)

    assert result["valid"], f"Invalid wetland corridor plan: {result['errors']}"
    assert result["total_score"] == optimal_total, (
        f"Expected optimal total_score {optimal_total}, got {result['total_score']}"
    )
    assert canonical_key(solution) == canonical_key(optimal_plan), (
        f"Expected optimal plan {optimal_plan}, got {solution}"
    )


def main():
    scenario = load_scenario()
    solution = load_solution()
    result = evaluate_plan(solution, scenario)
    optimal_total, optimal_plan = compute_optimal_plan(scenario)

    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    SCORE_DIR.joinpath("wetland_corridor_plan.txt").write_text(f"{result['score']:.6f}")

    if not result["valid"]:
        raise SystemExit(f"Invalid wetland corridor plan: {result['errors']}")

    if result["total_score"] != optimal_total:
        raise SystemExit(
            f"Expected optimal total_score {optimal_total}, got {result['total_score']}"
        )

    if canonical_key(solution) != canonical_key(optimal_plan):
        raise SystemExit(f"Expected optimal plan {optimal_plan}, got {solution}")

    print(
        "Validated wetland corridor plan with total_score="
        f"{result['total_score']} and score={result['score']:.3f}"
    )


if __name__ == "__main__":
    main()
