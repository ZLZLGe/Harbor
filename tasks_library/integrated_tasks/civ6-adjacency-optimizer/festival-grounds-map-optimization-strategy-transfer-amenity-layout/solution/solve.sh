#!/bin/bash

python3 <<'PY'
import json
import os
from itertools import combinations
from pathlib import Path

SCENARIO_PATH = Path(os.environ.get("SCENARIO_PATH", "/data/festival_scenario.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/output/festival_layout_plan.json"))


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


with open(SCENARIO_PATH) as f:
    scenario = json.load(f)

site_map = {
    tuple(site["coord"]): site
    for site in scenario["candidate_sites"]
}
prohibited = {
    tuple(site["coord"])
    for site in scenario["prohibited_sites"]
}
quiet_tiles = [
    tuple(coord)
    for coord in scenario["stage_noise_buffer"]["quiet_zone_tiles"]
]


def role_coords(plan, role):
    if role == "MAIN_STAGE":
        return [plan["main_stage"]]
    if role == "FIRST_AID":
        return [plan["first_aid_station"]]
    if role == "FOOD_COURT":
        return list(plan["food_courts"])
    if role == "WATER_POINT":
        return list(plan["water_points"])
    raise KeyError(role)


def plan_signature(plan):
    return (
        plan["main_stage"],
        *sorted(plan["food_courts"]),
        *sorted(plan["water_points"]),
        plan["first_aid_station"],
    )


def validate_plan(plan):
    used = [
        plan["main_stage"],
        plan["first_aid_station"],
        *plan["food_courts"],
        *plan["water_points"],
    ]
    if len(set(used)) != 6:
        return False
    if any(coord not in site_map for coord in used):
        return False
    if any(coord in prohibited for coord in used):
        return False
    if any(coord in map(tuple, scenario["evacuation_corridors"]) for coord in used):
        return False
    for quiet in quiet_tiles:
        if manhattan(plan["main_stage"], quiet) < scenario["stage_noise_buffer"]["min_distance"]:
            return False
    for rule in scenario["safety_distance_rules"]:
        left_coords = role_coords(plan, rule["roles"][0])
        right_coords = role_coords(plan, rule["roles"][1])
        for left in left_coords:
            for right in right_coords:
                if left == right:
                    continue
                if manhattan(left, right) < rule["min_distance"]:
                    return False
    return True


def score_plan(plan):
    site_value = 0
    crowd_coverage_reward = 0
    support_bonus = 0
    distance_penalty = 0

    for role, coords in (
        ("MAIN_STAGE", [plan["main_stage"]]),
        ("FOOD_COURT", list(plan["food_courts"])),
        ("WATER_POINT", list(plan["water_points"])),
        ("FIRST_AID", [plan["first_aid_station"]]),
    ):
        radius = scenario["coverage_radius_by_role"][role]
        for coord in coords:
            site_value += site_map[coord]["role_site_values"][role]
            for hotspot in scenario["hotspots"]:
                if manhattan(coord, tuple(hotspot["coord"])) <= radius:
                    crowd_coverage_reward += round(
                        hotspot["crowd_weight"] * hotspot["role_weights"][role]
                    )

    for rule in scenario["support_bonus_rules"]:
        for source in role_coords(plan, rule["source_role"]):
            for target in role_coords(plan, rule["target_role"]):
                if manhattan(source, target) <= rule["max_distance"]:
                    support_bonus += rule["bonus"]

    for rule in scenario["distance_penalty_rules"]:
        distances = [
            manhattan(left, right)
            for left in role_coords(plan, rule["roles"][0])
            for right in role_coords(plan, rule["roles"][1])
            if left != right
        ]
        min_distance = min(distances)
        if min_distance > rule["max_distance"]:
            distance_penalty += (
                min_distance - rule["max_distance"]
            ) * rule["penalty_per_tile"]

    total_score = site_value + crowd_coverage_reward + support_bonus - distance_penalty
    return {
        "site_value": site_value,
        "crowd_coverage_reward": crowd_coverage_reward,
        "support_bonus": support_bonus,
        "distance_penalty": distance_penalty,
        "total_score": total_score,
    }


coordinates = sorted(site_map)
best_plan = None
best_signature = None
best_breakdown = None

for main_stage in coordinates:
    remaining_after_stage = [coord for coord in coordinates if coord != main_stage]
    for food_courts in combinations(remaining_after_stage, scenario["required_counts"]["FOOD_COURT"]):
        remaining_after_food = [
            coord for coord in remaining_after_stage
            if coord not in food_courts
        ]
        for water_points in combinations(remaining_after_food, scenario["required_counts"]["WATER_POINT"]):
            remaining_after_water = [
                coord for coord in remaining_after_food
                if coord not in water_points
            ]
            for first_aid_station in remaining_after_water:
                plan = {
                    "main_stage": main_stage,
                    "food_courts": tuple(sorted(food_courts)),
                    "water_points": tuple(sorted(water_points)),
                    "first_aid_station": first_aid_station,
                }
                if not validate_plan(plan):
                    continue
                breakdown = score_plan(plan)
                signature = plan_signature(plan)
                if best_plan is None:
                    best_plan = plan
                    best_signature = signature
                    best_breakdown = breakdown
                    continue
                if breakdown["total_score"] > best_breakdown["total_score"]:
                    best_plan = plan
                    best_signature = signature
                    best_breakdown = breakdown
                elif (
                    breakdown["total_score"] == best_breakdown["total_score"]
                    and signature < best_signature
                ):
                    best_plan = plan
                    best_signature = signature
                    best_breakdown = breakdown

if best_plan is None:
    raise SystemExit("No valid festival layout found.")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
output = {
    "main_stage": list(best_plan["main_stage"]),
    "food_courts": [list(coord) for coord in best_plan["food_courts"]],
    "water_points": [list(coord) for coord in best_plan["water_points"]],
    "first_aid_station": list(best_plan["first_aid_station"]),
    "score_breakdown": best_breakdown,
}

with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2)

print(json.dumps(output, indent=2))
PY
