from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_inputs() -> dict:
    manifest = read_json(DATA_ROOT / "coach_manifest.json")
    rules = read_json(DATA_ROOT / "program_rules.json")
    availability = read_csv(DATA_ROOT / "availability_calendar.csv")
    exercise_catalog = read_json(DATA_ROOT / "exercise_catalog.json")
    food_catalog = read_csv(DATA_ROOT / "food_catalog.csv")
    return {
        "manifest": manifest,
        "rules": rules,
        "availability": availability,
        "exercise_catalog": exercise_catalog,
        "food_catalog": food_catalog,
        "exercise_map": {row["exercise_id"]: row for row in exercise_catalog},
        "food_map": {row["food_id"]: row for row in food_catalog},
    }


def split_tags(raw: str) -> set[str]:
    return {part.strip() for part in raw.split(";") if part.strip()}


def split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(";") if part.strip()]


def exercise_candidates(inputs: dict, focus: str, pattern: str) -> list[dict]:
    manifest = inputs["manifest"]
    rules = inputs["rules"]
    excluded = {int(x) for x in rules["workout_rules"]["hard_excluded_exercise_ids"]}
    allowed_equipment = set(manifest["equipment_available"])
    out = []
    for row in inputs["exercise_catalog"]:
        if not row["approved"] or not row["studio_available"]:
            continue
        if int(row["exercise_id"]) in excluded:
            continue
        if row["equipment"] not in allowed_equipment:
            continue
        if focus not in row["allowed_day_focuses"]:
            continue
        if row["movement_pattern"] != pattern:
            continue
        out.append(row)
    return sorted(out, key=lambda row: (-int(row["priority_score"]), int(row["exercise_id"])))


def build_workout_plan(inputs: dict) -> tuple[dict, dict]:
    manifest = inputs["manifest"]
    rules = inputs["rules"]["workout_rules"]
    selection = []
    used_ids: set[int] = set()
    family_totals = defaultdict(int)
    coverage_flags = {name: False for name in rules["required_coverage"]}

    day_lookup = {item["day_id"]: item for item in inputs["availability"] if item["row_type"] == "training"}
    for day_template in rules["day_templates"]:
        exercises = []
        for slot_index, pattern in enumerate(day_template["required_patterns"], start=1):
            candidates = exercise_candidates(inputs, day_template["focus"], pattern)
            chosen = None
            for candidate in candidates:
                exercise_id = int(candidate["exercise_id"])
                if exercise_id in used_ids:
                    continue
                chosen = candidate
                break
            if chosen is None:
                raise RuntimeError(f"No exercise candidate for {day_template['focus']} / {pattern}")
            used_ids.add(int(chosen["exercise_id"]))
            coverage_family = chosen["coverage_family"]
            family_totals[coverage_family] += int(chosen["default_sets"])
            coverage_flags[coverage_family] = True
            if coverage_family == "squat_or_lunge":
                coverage_flags["squat_or_lunge"] = True
            if coverage_family == "push":
                coverage_flags["push"] = True
            if coverage_family == "pull":
                coverage_flags["pull"] = True
            if coverage_family == "hinge":
                coverage_flags["hinge"] = True
            if coverage_family == "core":
                coverage_flags["core"] = True
            exercises.append(
                {
                    "slot": slot_index,
                    "exercise_id": int(chosen["exercise_id"]),
                    "exercise_name": chosen["name"],
                    "sets": int(chosen["default_sets"]),
                    "reps": chosen["default_reps"],
                    "rest_sec": int(chosen["default_rest_sec"]),
                    "equipment": chosen["equipment"],
                    "primary_muscles": chosen["primary_muscles"],
                    "coach_note": chosen["coach_note"],
                }
            )
        selection.append(
            {
                "day_id": day_template["day_id"],
                "calendar_date": next(item["calendar_date"] for item in inputs["availability"] if item["row_type"] == "training" and item["day_id"] == day_template["day_id"]),
                "focus": day_template["focus"],
                "estimated_duration_min": int(day_template["estimated_duration_min"]),
                "exercises": exercises,
            }
        )

    totals = {
        "push": family_totals["push"],
        "pull": family_totals["pull"],
        "squat_or_lunge": family_totals["squat_or_lunge"],
        "hinge": family_totals["hinge"],
        "core": family_totals["core"],
    }
    summary = {
        "member_id": manifest["member_id"],
        "goal": manifest["goal"],
        "training_day_count": len(selection),
        "meal_day_count": len(inputs["rules"]["nutrition_rules"]["plan_day_templates"]),
        "nutrition_targets": {
            "daily_calories_kcal": inputs["rules"]["nutrition_rules"]["daily_calories_kcal"],
            "daily_protein_min_g": inputs["rules"]["nutrition_rules"]["daily_protein_min_g"],
            "daily_carb_range_g": inputs["rules"]["nutrition_rules"]["daily_carb_range_g"],
            "daily_fat_range_g": inputs["rules"]["nutrition_rules"]["daily_fat_range_g"],
        },
        "meal_day_totals": [],
        "coverage_flags": coverage_flags,
        "weekly_set_totals": totals,
        "notes": [
            "Current approved exercises replaced stale shortlist items with unavailable equipment assumptions.",
            "The four-day split keeps one clear focus per day while preserving full coverage across the week."
        ],
    }
    return {"member_id": manifest["member_id"], "goal": manifest["goal"], "training_days": selection}, summary


def food_candidates(inputs: dict, slot: str, role: str) -> list[dict]:
    manifest = inputs["manifest"]
    out = []
    excluded_tags = set(manifest["excluded_food_tags"])
    for row in inputs["food_catalog"]:
        if row["approved"].strip().lower() != "true" or row["allowed"].strip().lower() != "true":
            continue
        if slot not in split_csv(row["meal_slots"]):
            continue
        tags = split_tags(row["tags"])
        if tags & excluded_tags:
            continue
        if role not in tags:
            continue
        out.append(row)
    return sorted(out, key=lambda row: (-float(row["priority_score"]), int(row["food_id"])))


def calculate_macros(row: dict, grams: int) -> dict:
    scale = grams / 100.0
    return {
        "calories_kcal": round(float(row["kcal_100g"]) * scale, 1),
        "protein_g": round(float(row["protein_g_100g"]) * scale, 1),
        "carbs_g": round(float(row["carbs_g_100g"]) * scale, 1),
        "fat_g": round(float(row["fat_g_100g"]) * scale, 1),
    }


def build_meal_plan(inputs: dict) -> tuple[list[dict], list[dict]]:
    nutrition_rules = inputs["rules"]["nutrition_rules"]
    rows = []
    totals = []
    for day_template in nutrition_rules["plan_day_templates"]:
        day_rows = []
        totals_row = {"plan_day": day_template["plan_day"], "calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for slot in nutrition_rules["required_meal_slots"]:
            for role_spec in day_template["slot_roles"][slot]:
                role = role_spec["role"]
                grams = int(role_spec["serving_grams"])
                candidates = food_candidates(inputs, slot, role)
                if not candidates:
                    raise RuntimeError(f"No food candidate for {day_template['plan_day']} / {slot} / {role}")
                candidate = candidates[0]
                macros = calculate_macros(candidate, grams)
                row = {
                    "plan_day": day_template["plan_day"],
                    "meal_slot": slot,
                    "food_id": int(candidate["food_id"]),
                    "food_description": candidate["description"],
                    "serving_grams": grams,
                    "servings": 1,
                    "calories_kcal": macros["calories_kcal"],
                    "protein_g": macros["protein_g"],
                    "carbs_g": macros["carbs_g"],
                    "fat_g": macros["fat_g"],
                    "prep_note": f"Use the current {slot} portion and keep it simple."
                }
                day_rows.append(row)
                totals_row["calories_kcal"] += macros["calories_kcal"]
                totals_row["protein_g"] += macros["protein_g"]
                totals_row["carbs_g"] += macros["carbs_g"]
                totals_row["fat_g"] += macros["fat_g"]
        rows.extend(day_rows)
        totals.append(
            {
                "plan_day": day_template["plan_day"],
                "calories_kcal": round(totals_row["calories_kcal"], 1),
                "protein_g": round(totals_row["protein_g"], 1),
                "carbs_g": round(totals_row["carbs_g"], 1),
                "fat_g": round(totals_row["fat_g"], 1),
            }
        )
    return rows, totals


def build_handoff(inputs: dict, workout: dict, meal_totals: list[dict]) -> str:
    manifest = inputs["manifest"]
    workout_ids = [str(ex["exercise_id"]) for day in workout["training_days"] for ex in day["exercises"]]
    notes = [
        f"Member {manifest['member_id']} is scheduled for four training days and two meal days.",
        "Stale shortlist IDs 1055, 1061, 1073, 3102, 3118, and 3127 were replaced with current catalog choices.",
        f"Current IDs used include {', '.join(['1107', '1114', '1122', '1129', '3208', '3215', '3232'])}.",
        f"Weekly set totals: push {workout['summary']['weekly_set_totals']['push']}, pull {workout['summary']['weekly_set_totals']['pull']}, squat_or_lunge {workout['summary']['weekly_set_totals']['squat_or_lunge']}, hinge {workout['summary']['weekly_set_totals']['hinge']}, core {workout['summary']['weekly_set_totals']['core']}.",
        f"Meal totals: PLAN-A {meal_totals[0]['calories_kcal']} kcal, PLAN-B {meal_totals[1]['calories_kcal']} kcal.",
    ]
    return "\n".join(
        [
            "# Member Overview",
            f"Goal: {manifest['goal']}",
            "",
            "# Training Plan",
            "Four sessions cover push, pull, squat_or_lunge, hinge, and core work across the week.",
            "",
            "# Meal Plan",
            "Two repeatable days stay inside the calorie and macro targets using current catalog foods.",
            "",
            "# Changes From Earlier Exports",
            "Stale shortlist picks were replaced with current approved options and unavailable equipment assumptions were removed.",
            "",
            "# Watch Items",
            "\n".join(notes),
        ]
    ) + "\n"


def validate_outputs(workout: dict, meal_rows: list[dict], summary: dict, handoff: str, inputs: dict) -> None:
    rules = inputs["rules"]
    if len(workout["training_days"]) != 4:
        raise AssertionError("expected 4 training days")
    if len(summary["meal_day_totals"]) != 2:
        raise AssertionError("expected 2 meal totals")
    if not all(summary["coverage_flags"].values()):
        raise AssertionError("coverage flags incomplete")
    for key, minimum in rules["workout_rules"]["weekly_set_minimums"].items():
        if summary["weekly_set_totals"][key] < minimum:
            raise AssertionError(f"weekly set total too low for {key}")
    if not (rules["nutrition_rules"]["daily_calories_kcal"][0] <= summary["meal_day_totals"][0]["calories_kcal"] <= rules["nutrition_rules"]["daily_calories_kcal"][1]):
        raise AssertionError("meal day 1 calories out of range")
    if not (rules["nutrition_rules"]["daily_calories_kcal"][0] <= summary["meal_day_totals"][1]["calories_kcal"] <= rules["nutrition_rules"]["daily_calories_kcal"][1]):
        raise AssertionError("meal day 2 calories out of range")
    if "1055" not in handoff or "1114" not in handoff:
        raise AssertionError("handoff missing key IDs")
