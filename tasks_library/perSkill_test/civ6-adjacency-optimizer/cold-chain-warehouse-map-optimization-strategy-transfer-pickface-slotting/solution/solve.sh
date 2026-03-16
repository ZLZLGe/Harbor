#!/bin/bash
set -euo pipefail

SCENARIO_PATH="${SCENARIO_PATH:-/data/warehouse_scenario.json}"
OUTPUT_PATH="${OUTPUT_PATH:-/output/warehouse_slotting_plan.json}"
export SCENARIO_PATH OUTPUT_PATH

python3 - <<'PY'
import json
import os
from collections import deque
from itertools import combinations
from pathlib import Path


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

    def travel_distance(self, slot_a, slot_b):
        key = tuple(sorted((slot_a, slot_b)))
        if key in self.travel_cache:
            return self.travel_cache[key]

        starts = self.slot_access[slot_a]
        targets = set(self.slot_access[slot_b])
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

    def is_slot_reachable(self, slot_coord):
        return bool(self.slot_access[slot_coord])


def evaluate_layout(model, pickfaces, buffer_coord, replenishment_coord, charger_coord):
    assignments = [
        ("PICKFACE", pickfaces[0]),
        ("PICKFACE", pickfaces[1]),
        ("BUFFER", buffer_coord),
        ("REPLENISHMENT", replenishment_coord),
        ("CHARGER", charger_coord),
    ]

    if len({coord for _, coord in assignments}) != len(assignments):
        return None

    for coord in (pickfaces[0], pickfaces[1], buffer_coord, replenishment_coord, charger_coord):
        if coord not in model.slots or not model.is_slot_reachable(coord):
            return None

    for rule in model.scenario["min_spacing"]:
        roles = rule["roles"]
        distance = rule["distance"]
        if roles == ["PICKFACE", "PICKFACE"]:
            if manhattan(pickfaces[0], pickfaces[1]) < distance:
                return None
        elif roles == ["CHARGER", "PICKFACE"]:
            if any(manhattan(charger_coord, pf_coord) < distance for pf_coord in pickfaces):
                return None

    zone_usage = {zone: 0 for zone in model.zone_capacity_limits}
    throughput_reward = 0
    handling_cost = 0
    congestion_penalty = 0
    capacity_used = 0

    for role, coord in assignments:
        slot = model.slots[coord]
        metrics = slot["role_metrics"][role]
        zone_usage[slot["zone"]] += model.capacity_loads[role]
        if zone_usage[slot["zone"]] > model.zone_capacity_limits[slot["zone"]]:
            return None
        throughput_reward += metrics["throughput"]
        handling_cost += metrics["handling_cost"]
        congestion_penalty += metrics["congestion"]
        capacity_used += model.capacity_loads[role]

    named_coords = {
        "BUFFER": buffer_coord,
        "REPLENISHMENT": replenishment_coord,
        "CHARGER": charger_coord,
    }
    for index, pf_coord in enumerate(pickfaces):
        named_coords[f"PICKFACE_{index}"] = pf_coord

    for rule in model.scenario["support_bonus_rules"]:
        source_role = rule["source_role"]
        target_role = rule["target_role"]
        max_distance = rule["max_travel_distance"]
        bonus = rule["throughput_bonus"]

        if source_role == "PICKFACE":
            for pf_coord in pickfaces:
                travel = model.travel_distance(pf_coord, named_coords[target_role])
                if travel is not None and travel <= max_distance:
                    throughput_reward += bonus
        else:
            travel = model.travel_distance(named_coords[source_role], named_coords[target_role])
            if travel is not None and travel <= max_distance:
                throughput_reward += bonus

    for rule in model.scenario["extra_congestion_rules"]:
        if "roles" in rule:
            first, second = rule["roles"]
            travel = model.travel_distance(named_coords[first], named_coords[second])
            if travel is not None and travel <= rule["max_travel_distance"]:
                congestion_penalty += rule["penalty"]
        elif "same_zone" in rule:
            first, second = rule["same_zone"]
            if model.slots[named_coords[first]]["zone"] == model.slots[named_coords[second]]["zone"]:
                congestion_penalty += rule["penalty"]

    total_score = throughput_reward - handling_cost - congestion_penalty
    return {
        "pickfaces": [[pickfaces[0][0], pickfaces[0][1]], [pickfaces[1][0], pickfaces[1][1]]],
        "buffer": [buffer_coord[0], buffer_coord[1]],
        "replenishment": [replenishment_coord[0], replenishment_coord[1]],
        "charger": [charger_coord[0], charger_coord[1]],
        "capacity_used": capacity_used,
        "score_breakdown": {
            "throughput_reward": throughput_reward,
            "handling_cost": handling_cost,
            "congestion_penalty": congestion_penalty,
            "total_score": total_score,
        },
    }


scenario_path = Path(os.environ["SCENARIO_PATH"])
output_path = Path(os.environ["OUTPUT_PATH"])

with open(scenario_path) as f:
    scenario = json.load(f)

model = ScenarioModel(scenario)
all_slots = sorted(model.slots)

best_layout = None
best_key = None

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
                layout = evaluate_layout(
                    model,
                    pickfaces,
                    buffer_coord,
                    replenishment_coord,
                    charger_coord,
                )
                if layout is None:
                    continue
                key = (
                    layout["score_breakdown"]["total_score"],
                    layout["score_breakdown"]["throughput_reward"],
                    -layout["score_breakdown"]["congestion_penalty"],
                    tuple(layout["pickfaces"]),
                    tuple(layout["buffer"]),
                    tuple(layout["replenishment"]),
                    tuple(layout["charger"]),
                )
                if best_key is None or key > best_key:
                    best_key = key
                    best_layout = layout

if best_layout is None:
    raise SystemExit("No legal warehouse layout found.")

output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(best_layout, f, indent=2)

print(
    "Wrote warehouse slotting plan to "
    f"{output_path} with total_score={best_layout['score_breakdown']['total_score']}"
)
PY
