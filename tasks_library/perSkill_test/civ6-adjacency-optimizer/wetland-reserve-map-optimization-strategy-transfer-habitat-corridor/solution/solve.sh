#!/bin/bash
set -euo pipefail

SCENARIO_PATH="${SCENARIO_PATH:-/data/wetland_reserve_scenario.json}"
OUTPUT_PATH="${OUTPUT_PATH:-/output/wetland_corridor_plan.json}"
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
    with open(Path(os.environ["SCENARIO_PATH"])) as f:
        return json.load(f)


def evaluate_layout(model, nests, buffers, monitor):
    nests = tuple(nests)
    buffers = tuple(buffers)
    assignments = [
        ("NEST_BOX", nests[0]),
        ("NEST_BOX", nests[1]),
        ("BUFFER", buffers[0]),
        ("BUFFER", buffers[1]),
        ("MONITOR", monitor),
    ]

    coords_only = [coord for _, coord in assignments]
    if len(set(coords_only)) != len(coords_only):
        return None

    if manhattan(nests[0], nests[1]) < 4:
        return None

    if any(manhattan(monitor, nest) < 3 for nest in nests):
        return None

    zone_capacity_used = {zone: 0 for zone in model.zone_capacity_limits}
    base_habitat = 0
    installation_cost = 0
    noise_penalty = 0

    for role, coord in assignments:
        site = model.open_sites.get(coord)
        if site is None:
            return None
        if not model.site_access.get(coord):
            return None

        zone = site["zone"]
        zone_capacity_used[zone] += model.zone_capacity_costs[role]
        if zone_capacity_used[zone] > model.zone_capacity_limits[zone]:
            return None

        metrics = site["role_metrics"][role]
        base_habitat += metrics["habitat_value"]
        installation_cost += metrics["installation_cost"]
        noise_penalty += site["noise_level"] * model.noise_penalty_weights[role]

    coverage_bonus = 0
    for patch in model.habitat_patches:
        patch_coord = patch["coord"]

        if any(
            (distance := model.site_to_patch_distance(nest, patch_coord)) is not None
            and distance <= model.coverage_radius["NEST_BOX"]
            for nest in nests
        ):
            coverage_bonus += patch["nest_bonus"]

        if any(
            (distance := model.site_to_patch_distance(buffer_coord, patch_coord)) is not None
            and distance <= model.coverage_radius["BUFFER"]
            for buffer_coord in buffers
        ):
            coverage_bonus += patch["buffer_bonus"]

        monitor_distance = model.site_to_patch_distance(monitor, patch_coord)
        if monitor_distance is not None and monitor_distance <= model.coverage_radius["MONITOR"]:
            coverage_bonus += patch["monitor_bonus"]

    support_bonus = 0
    for rule in model.support_bonus_rules:
        if rule["source_role"] == "NEST_BOX":
            for nest in nests:
                if any(
                    (distance := model.site_to_site_distance(nest, buffer_coord)) is not None
                    and distance <= rule["max_travel_distance"]
                    for buffer_coord in buffers
                ):
                    support_bonus += rule["bonus"]
        elif rule["source_role"] == "MONITOR":
            if any(
                (distance := model.site_to_site_distance(monitor, buffer_coord)) is not None
                and distance <= rule["max_travel_distance"]
                for buffer_coord in buffers
            ):
                support_bonus += rule["bonus"]

    network_bonus = model.network_bonus["bonus"] if model.is_network_connected(coords_only) else 0
    total_score = (
        base_habitat
        + coverage_bonus
        + support_bonus
        + network_bonus
        - installation_cost
        - noise_penalty
    )

    return {
        "nest_boxes": [[nests[0][0], nests[0][1]], [nests[1][0], nests[1][1]]],
        "buffers": [[buffers[0][0], buffers[0][1]], [buffers[1][0], buffers[1][1]]],
        "monitoring_point": [monitor[0], monitor[1]],
        "zone_capacity_used": zone_capacity_used,
        "score_breakdown": {
            "base_habitat": base_habitat,
            "coverage_bonus": coverage_bonus,
            "support_bonus": support_bonus,
            "network_bonus": network_bonus,
            "installation_cost": installation_cost,
            "noise_penalty": noise_penalty,
            "total_score": total_score,
        },
    }


def canonical_key(plan):
    score = plan["score_breakdown"]
    return (
        score["total_score"],
        score["coverage_bonus"],
        score["support_bonus"],
        -score["noise_penalty"],
        -score["installation_cost"],
        tuple(plan["nest_boxes"]),
        tuple(plan["buffers"]),
        tuple(plan["monitoring_point"]),
    )


scenario = load_scenario()
model = ScenarioModel(scenario)
open_coords = sorted(model.open_sites)

best_plan = None
best_key = None

for nests in combinations(open_coords, 2):
    remaining_after_nests = [coord for coord in open_coords if coord not in nests]
    for buffers in combinations(remaining_after_nests, 2):
        remaining_after_buffers = [
            coord
            for coord in remaining_after_nests
            if coord not in buffers
        ]
        for monitor in remaining_after_buffers:
            plan = evaluate_layout(model, nests, buffers, monitor)
            if plan is None:
                continue
            key = canonical_key(plan)
            if best_key is None or key > best_key:
                best_key = key
                best_plan = plan

if best_plan is None:
    raise SystemExit("No legal wetland corridor plan found.")

output_path = Path(os.environ["OUTPUT_PATH"])
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(best_plan, f, indent=2)

print(
    "Wrote wetland corridor plan to "
    f"{output_path} with total_score={best_plan['score_breakdown']['total_score']}"
)
PY
