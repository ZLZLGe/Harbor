#!/usr/bin/env python3

import json
import os
from itertools import combinations
from pathlib import Path

SCENARIO_PATH = Path(os.environ.get("SCENARIO_PATH", "/data/festival_scenario.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/output/festival_layout_plan.json"))
SCORE_DIR = Path(os.environ.get("SCORE_DIR", "/logs/verifier/scores"))


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def load_scenario():
    with open(SCENARIO_PATH) as f:
        return json.load(f)


def load_solution():
    with open(OUTPUT_PATH) as f:
        return json.load(f)


class FestivalModel:
    def __init__(self, scenario):
        self.scenario = scenario
        self.site_map = {
            tuple(site["coord"]): site
            for site in scenario["candidate_sites"]
        }
        self.prohibited = {
            tuple(site["coord"])
            for site in scenario["prohibited_sites"]
        }
        self.corridors = {
            tuple(coord)
            for coord in scenario["evacuation_corridors"]
        }
        self.quiet_tiles = [
            tuple(coord)
            for coord in scenario["stage_noise_buffer"]["quiet_zone_tiles"]
        ]

    def role_coords(self, plan, role):
        if role == "MAIN_STAGE":
            return [plan["main_stage"]]
        if role == "FIRST_AID":
            return [plan["first_aid_station"]]
        if role == "FOOD_COURT":
            return list(plan["food_courts"])
        if role == "WATER_POINT":
            return list(plan["water_points"])
        raise KeyError(role)

    def plan_signature(self, plan):
        return (
            plan["main_stage"],
            *sorted(plan["food_courts"]),
            *sorted(plan["water_points"]),
            plan["first_aid_station"],
        )

    def validate_plan(self, plan):
        errors = []
        used = [
            plan["main_stage"],
            plan["first_aid_station"],
            *plan["food_courts"],
            *plan["water_points"],
        ]

        if len(set(used)) != 6:
            errors.append("All six facilities must use distinct coordinates")

        for coord in used:
            if coord not in self.site_map:
                errors.append(f"Unknown candidate site: {coord}")

        for coord in used:
            if coord in self.prohibited:
                errors.append(f"Prohibited site used: {coord}")

        for coord in used:
            if coord in self.corridors:
                errors.append(f"Evacuation corridor must remain empty: {coord}")

        min_noise_distance = self.scenario["stage_noise_buffer"]["min_distance"]
        for quiet in self.quiet_tiles:
            if manhattan(plan["main_stage"], quiet) < min_noise_distance:
                errors.append(
                    f"Main stage at {plan['main_stage']} violates the quiet-zone buffer"
                )
                break

        for rule in self.scenario["safety_distance_rules"]:
            left_coords = self.role_coords(plan, rule["roles"][0])
            right_coords = self.role_coords(plan, rule["roles"][1])
            for left in left_coords:
                for right in right_coords:
                    if left == right:
                        continue
                    if manhattan(left, right) < rule["min_distance"]:
                        errors.append(
                            f"{rule['roles'][0]} and {rule['roles'][1]} are too close at {left} and {right}"
                        )

        return errors

    def score_plan(self, plan):
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
            radius = self.scenario["coverage_radius_by_role"][role]
            for coord in coords:
                site_value += self.site_map[coord]["role_site_values"][role]
                for hotspot in self.scenario["hotspots"]:
                    hotspot_coord = tuple(hotspot["coord"])
                    if manhattan(coord, hotspot_coord) <= radius:
                        crowd_coverage_reward += round(
                            hotspot["crowd_weight"] * hotspot["role_weights"][role]
                        )

        for rule in self.scenario["support_bonus_rules"]:
            for source in self.role_coords(plan, rule["source_role"]):
                for target in self.role_coords(plan, rule["target_role"]):
                    if manhattan(source, target) <= rule["max_distance"]:
                        support_bonus += rule["bonus"]

        for rule in self.scenario["distance_penalty_rules"]:
            distances = [
                manhattan(left, right)
                for left in self.role_coords(plan, rule["roles"][0])
                for right in self.role_coords(plan, rule["roles"][1])
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

    def compute_optimal_plan(self):
        coordinates = sorted(self.site_map)
        best_plan = None
        best_signature = None
        best_breakdown = None

        for main_stage in coordinates:
            remaining_after_stage = [coord for coord in coordinates if coord != main_stage]
            for food_courts in combinations(
                remaining_after_stage,
                self.scenario["required_counts"]["FOOD_COURT"],
            ):
                remaining_after_food = [
                    coord for coord in remaining_after_stage
                    if coord not in food_courts
                ]
                for water_points in combinations(
                    remaining_after_food,
                    self.scenario["required_counts"]["WATER_POINT"],
                ):
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
                        if self.validate_plan(plan):
                            continue
                        breakdown = self.score_plan(plan)
                        signature = self.plan_signature(plan)
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

        return best_plan, best_breakdown


def parse_solution(solution):
    errors = []
    required_keys = {
        "main_stage",
        "food_courts",
        "water_points",
        "first_aid_station",
        "score_breakdown",
    }
    missing = sorted(required_keys - set(solution))
    if missing:
        errors.append(f"Missing required keys: {missing}")

    extra = sorted(set(solution) - required_keys)
    if extra:
        errors.append(f"Unexpected extra keys: {extra}")

    if errors:
        return None, errors

    def parse_coord(name, value):
        if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, int) for v in value):
            errors.append(f"{name} must be [x, y] with integers")
            return None
        return tuple(value)

    main_stage = parse_coord("main_stage", solution["main_stage"])
    first_aid_station = parse_coord("first_aid_station", solution["first_aid_station"])

    def parse_coord_list(name, values, expected_len):
        if not isinstance(values, list) or len(values) != expected_len:
            errors.append(f"{name} must contain exactly {expected_len} coordinates")
            return []
        parsed = []
        for index, coord in enumerate(values):
            parsed_coord = parse_coord(f"{name}[{index}]", coord)
            if parsed_coord is not None:
                parsed.append(parsed_coord)
        return parsed

    food_courts = parse_coord_list("food_courts", solution["food_courts"], 2)
    water_points = parse_coord_list("water_points", solution["water_points"], 2)

    if food_courts and food_courts != sorted(food_courts):
        errors.append("food_courts must be sorted lexicographically")
    if water_points and water_points != sorted(water_points):
        errors.append("water_points must be sorted lexicographically")

    breakdown = solution["score_breakdown"]
    if not isinstance(breakdown, dict):
        errors.append("score_breakdown must be an object")
        breakdown = {}

    for key in (
        "site_value",
        "crowd_coverage_reward",
        "support_bonus",
        "distance_penalty",
        "total_score",
    ):
        if key not in breakdown or not isinstance(breakdown[key], int):
            errors.append(f"score_breakdown.{key} must be an integer")

    if errors:
        return None, errors

    computed_total = (
        breakdown["site_value"]
        + breakdown["crowd_coverage_reward"]
        + breakdown["support_bonus"]
        - breakdown["distance_penalty"]
    )
    if breakdown["total_score"] != computed_total:
        errors.append(
            "score_breakdown.total_score does not match the required formula"
        )

    plan = {
        "main_stage": main_stage,
        "food_courts": tuple(food_courts),
        "water_points": tuple(water_points),
        "first_aid_station": first_aid_station,
    }
    return plan, errors

def fail(message):
    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    (SCORE_DIR / "festival_layout_plan.txt").write_text("0.0")
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main():
    SCORE_DIR.mkdir(parents=True, exist_ok=True)

    if not OUTPUT_PATH.exists():
        fail(f"Solution file not found: {OUTPUT_PATH}")

    scenario = load_scenario()
    model = FestivalModel(scenario)

    try:
        solution = load_solution()
    except json.JSONDecodeError as exc:
        fail(f"Solution is not valid JSON: {exc}")

    if not isinstance(solution, dict):
        fail("Solution must be a JSON object")

    plan, parse_errors = parse_solution(solution)
    if parse_errors:
        fail("; ".join(parse_errors))

    validation_errors = model.validate_plan(plan)
    if validation_errors:
        fail("; ".join(validation_errors))

    expected_breakdown = model.score_plan(plan)
    for key, expected in expected_breakdown.items():
        actual = solution["score_breakdown"][key]
        if actual != expected:
            fail(f"score_breakdown.{key} = {actual}, expected {expected}")

    optimal_plan, optimal_breakdown = model.compute_optimal_plan()
    optimal_score = optimal_breakdown["total_score"]
    actual_score = expected_breakdown["total_score"]
    score = actual_score / optimal_score
    (SCORE_DIR / "festival_layout_plan.txt").write_text(str(score))

    if actual_score != optimal_score:
        fail(f"Layout is valid but not optimal: got {actual_score}, optimal is {optimal_score}")

    expected_signature = model.plan_signature(optimal_plan)
    actual_signature = model.plan_signature(plan)
    if actual_signature != expected_signature:
        fail("Layout does not match the required tie-break ordering for optimal plans")

    print("PASS: festival layout is valid and optimal")
    print(f"Optimal total_score: {optimal_score}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        fail(f"Unexpected verifier error: {exc}")
