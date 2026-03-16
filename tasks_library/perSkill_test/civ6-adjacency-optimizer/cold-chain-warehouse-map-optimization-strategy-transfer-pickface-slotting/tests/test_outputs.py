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


SCENARIO_PATH = Path(os.environ.get("SCENARIO_PATH", "/data/warehouse_scenario.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/output/warehouse_slotting_plan.json"))
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
        self.aisles = {tuple(coord) for coord in scenario["aisles"]}
        self.dock = tuple(scenario["dock"])
        self.slots = {
            tuple(slot["coord"]): slot
            for slot in scenario["slots"]
        }
        self.required_counts = scenario["required_counts"]
        self.capacity_loads = scenario["capacity_loads"]
        self.zone_capacity_limits = scenario["zone_capacity_limits"]
        self.reachable_aisles = self._compute_reachable_aisles()
        self.slot_access = {
            coord: [
                aisle for aisle in self._adjacent_aisles(coord)
                if aisle in self.reachable_aisles
            ]
            for coord in self.slots
        }
        self.travel_cache = {}

    def _compute_reachable_aisles(self):
        queue = deque([self.dock])
        visited = {self.dock}
        while queue:
            current = queue.popleft()
            for neighbor in orthogonal_neighbors(current):
                if neighbor in self.aisles and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def _adjacent_aisles(self, slot_coord):
        return [
            neighbor
            for neighbor in orthogonal_neighbors(slot_coord)
            if neighbor in self.aisles
        ]

    def is_slot_reachable(self, slot_coord):
        return bool(self.slot_access.get(slot_coord))

    def travel_distance(self, slot_a, slot_b):
        key = tuple(sorted((slot_a, slot_b)))
        if key in self.travel_cache:
            return self.travel_cache[key]

        starts = self.slot_access.get(slot_a, [])
        targets = set(self.slot_access.get(slot_b, []))
        if not starts or not targets:
            self.travel_cache[key] = None
            return None

        best = None
        for start in starts:
            queue = deque([(start, 0)])
            visited = {start}
            while queue:
                current, dist = queue.popleft()
                if current in targets:
                    candidate = dist + 2
                    if best is None or candidate < best:
                        best = candidate
                    break
                for neighbor in orthogonal_neighbors(current):
                    if neighbor in self.reachable_aisles and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))

        self.travel_cache[key] = best
        return best


def load_scenario():
    with open(SCENARIO_PATH) as f:
        return json.load(f)


def load_solution():
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def score_layout(model, pickface_coords, buffer_tuple, replenishment_tuple, charger_tuple):
    errors = []
    named_assignments = [
        ("PICKFACE", pickface_coords[0]),
        ("PICKFACE", pickface_coords[1]),
        ("BUFFER", buffer_tuple),
        ("REPLENISHMENT", replenishment_tuple),
        ("CHARGER", charger_tuple),
    ]

    if len({coord for _, coord in named_assignments}) != len(named_assignments):
        errors.append("All facilities must occupy distinct coordinates")

    for role, coord in named_assignments:
        if coord not in model.slots:
            errors.append(f"{role} uses unknown slot {coord}")
            continue
        if not model.is_slot_reachable(coord):
            errors.append(f"{role} uses unreachable slot {coord}")

    if manhattan(pickface_coords[0], pickface_coords[1]) < 4:
        errors.append("PICKFACE coordinates violate the minimum spacing of 4")

    for pf_coord in pickface_coords:
        if manhattan(charger_tuple, pf_coord) < 3:
            errors.append("CHARGER must be at least Manhattan distance 3 from every PICKFACE")

    zone_usage = {zone: 0 for zone in model.zone_capacity_limits}
    throughput_reward = 0
    handling_cost = 0
    congestion_penalty = 0
    capacity_used = 0

    for role, coord in named_assignments:
        slot = model.slots.get(coord)
        if slot is None:
            continue
        metrics = slot["role_metrics"][role]
        zone_usage[slot["zone"]] += model.capacity_loads[role]
        throughput_reward += metrics["throughput"]
        handling_cost += metrics["handling_cost"]
        congestion_penalty += metrics["congestion"]
        capacity_used += model.capacity_loads[role]

    for zone, used in zone_usage.items():
        if used > model.zone_capacity_limits[zone]:
            errors.append(f"Zone {zone} uses {used} capacity, exceeding {model.zone_capacity_limits[zone]}")

    role_coords = {
        "BUFFER": buffer_tuple,
        "REPLENISHMENT": replenishment_tuple,
        "CHARGER": charger_tuple,
    }

    for rule in model.scenario["support_bonus_rules"]:
        if rule["source_role"] == "PICKFACE":
            target = role_coords[rule["target_role"]]
            for pf_coord in pickface_coords:
                travel = model.travel_distance(pf_coord, target)
                if travel is not None and travel <= rule["max_travel_distance"]:
                    throughput_reward += rule["throughput_bonus"]
        else:
            source = role_coords[rule["source_role"]]
            target = role_coords[rule["target_role"]]
            travel = model.travel_distance(source, target)
            if travel is not None and travel <= rule["max_travel_distance"]:
                throughput_reward += rule["throughput_bonus"]

    for rule in model.scenario["extra_congestion_rules"]:
        if "roles" in rule:
            first = role_coords[rule["roles"][0]]
            second = role_coords[rule["roles"][1]]
            travel = model.travel_distance(first, second)
            if travel is not None and travel <= rule["max_travel_distance"]:
                congestion_penalty += rule["penalty"]
        elif "same_zone" in rule:
            first = role_coords[rule["same_zone"][0]]
            second = role_coords[rule["same_zone"][1]]
            if model.slots[first]["zone"] == model.slots[second]["zone"]:
                congestion_penalty += rule["penalty"]

    total_score = throughput_reward - handling_cost - congestion_penalty

    return {
        "errors": errors,
        "capacity_used": capacity_used,
        "throughput_reward": throughput_reward,
        "handling_cost": handling_cost,
        "congestion_penalty": congestion_penalty,
        "total_score": total_score,
    }


def evaluate_solution(solution, scenario):
    errors = []
    model = ScenarioModel(scenario)

    if not isinstance(solution, dict):
        return {"valid": False, "errors": ["Solution must be a JSON object"], "score": 0.0}

    required_keys = {"pickfaces", "buffer", "replenishment", "charger", "capacity_used", "score_breakdown"}
    for key in required_keys:
        if key not in solution:
            errors.append(f"Missing required key: {key}")
    if errors:
        return {"valid": False, "errors": errors, "score": 0.0}

    pickfaces = solution["pickfaces"]
    buffer_coord = solution["buffer"]
    replenishment_coord = solution["replenishment"]
    charger_coord = solution["charger"]
    score_breakdown = solution["score_breakdown"]

    if not isinstance(pickfaces, list) or len(pickfaces) != scenario["required_counts"]["PICKFACE"]:
        errors.append("pickfaces must contain exactly two coordinates")
        pickface_coords = []
    else:
        pickface_coords = []
        for index, coord in enumerate(pickfaces):
            if not isinstance(coord, list) or len(coord) != 2 or not all(isinstance(v, int) for v in coord):
                errors.append(f"pickfaces[{index}] must be [x, y] with integers")
            else:
                pickface_coords.append(tuple(coord))

    def parse_named_coord(name, value):
        if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, int) for v in value):
            errors.append(f"{name} must be [x, y] with integers")
            return None
        return tuple(value)

    buffer_tuple = parse_named_coord("buffer", buffer_coord)
    replenishment_tuple = parse_named_coord("replenishment", replenishment_coord)
    charger_tuple = parse_named_coord("charger", charger_coord)

    if not isinstance(solution["capacity_used"], int):
        errors.append("capacity_used must be an integer")

    if not isinstance(score_breakdown, dict):
        errors.append("score_breakdown must be an object")
        score_breakdown = {}

    for key in ("throughput_reward", "handling_cost", "congestion_penalty", "total_score"):
        if key not in score_breakdown or not isinstance(score_breakdown[key], int):
            errors.append(f"score_breakdown.{key} must be an integer")

    if errors:
        return {"valid": False, "errors": errors, "score": 0.0}

    computed = score_layout(
        model,
        pickface_coords,
        buffer_tuple,
        replenishment_tuple,
        charger_tuple,
    )
    errors.extend(computed["errors"])

    if solution["capacity_used"] != computed["capacity_used"]:
        errors.append(
            f"capacity_used {solution['capacity_used']} does not match calculated value {computed['capacity_used']}"
        )

    expected_breakdown = {
        "throughput_reward": computed["throughput_reward"],
        "handling_cost": computed["handling_cost"],
        "congestion_penalty": computed["congestion_penalty"],
        "total_score": computed["total_score"],
    }
    for key, expected in expected_breakdown.items():
        if score_breakdown.get(key) != expected:
            errors.append(
                f"score_breakdown.{key} = {score_breakdown.get(key)} but expected {expected}"
            )

    optimal_total, _ = compute_optimal_plan(scenario)
    valid = not errors
    score = (computed["total_score"] / optimal_total) if valid else 0.0

    return {
        "valid": valid,
        "errors": errors,
        "total_score": computed["total_score"],
        "optimal_total": optimal_total,
        "score": score,
    }


def compute_optimal_plan(scenario):
    model = ScenarioModel(scenario)
    all_slots = sorted(model.slots)
    best_score = None
    best_plan = None

    for pickfaces in combinations(all_slots, 2):
        remaining_after_pickfaces = [coord for coord in all_slots if coord not in pickfaces]
        for buffer_coord in remaining_after_pickfaces:
            remaining_after_buffer = [coord for coord in remaining_after_pickfaces if coord != buffer_coord]
            for replenishment_coord in remaining_after_buffer:
                remaining_after_replenishment = [
                    coord for coord in remaining_after_buffer
                    if coord != replenishment_coord
                ]
                for charger_coord in remaining_after_replenishment:
                    computed = score_layout(
                        model,
                        pickfaces,
                        buffer_coord,
                        replenishment_coord,
                        charger_coord,
                    )
                    if computed["errors"]:
                        continue
                    score_key = (
                        computed["total_score"],
                        computed["throughput_reward"],
                        -computed["congestion_penalty"],
                        pickfaces,
                        buffer_coord,
                        replenishment_coord,
                        charger_coord,
                    )
                    if best_score is None or score_key > best_score:
                        best_score = score_key
                        best_plan = {
                            "pickfaces": [[pickfaces[0][0], pickfaces[0][1]], [pickfaces[1][0], pickfaces[1][1]]],
                            "buffer": [buffer_coord[0], buffer_coord[1]],
                            "replenishment": [replenishment_coord[0], replenishment_coord[1]],
                            "charger": [charger_coord[0], charger_coord[1]],
                            "capacity_used": computed["capacity_used"],
                            "score_breakdown": {
                                "throughput_reward": computed["throughput_reward"],
                                "handling_cost": computed["handling_cost"],
                                "congestion_penalty": computed["congestion_penalty"],
                                "total_score": computed["total_score"],
                            },
                        }

    if best_score is None or best_plan is None:
        raise RuntimeError("No legal plan exists for the warehouse scenario")

    return best_score[0], best_plan


@pytest.fixture(scope="session", autouse=True)
def setup_score_dir():
    SCORE_DIR.mkdir(parents=True, exist_ok=True)


class TestFormat:
    def test_output_exists(self):
        assert OUTPUT_PATH.exists(), f"Solution file not found: {OUTPUT_PATH}"

    def test_output_json(self):
        with open(OUTPUT_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict), "Output must be a JSON object"


class TestEvaluation:
    def test_solution(self):
        scenario = load_scenario()
        solution = load_solution()
        result = evaluate_solution(solution, scenario)
        SCORE_DIR.mkdir(parents=True, exist_ok=True)
        (SCORE_DIR / "warehouse_slotting_plan.txt").write_text(str(result["score"]))
        assert result["valid"], f"Invalid solution: {result['errors']}"


if __name__ == "__main__":
    scenario = load_scenario()
    solution = load_solution()
    result = evaluate_solution(solution, scenario)
    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    (SCORE_DIR / "warehouse_slotting_plan.txt").write_text(str(result["score"]))
    if result["valid"]:
        print(f"Valid solution with score ratio {result['score']:.6f}")
    else:
        print("Invalid solution:")
        for error in result["errors"]:
            print(f"- {error}")
        raise SystemExit(1)
