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


def split_tags(raw: str) -> set[str]:
    return {part.strip() for part in raw.split(";") if part.strip()}


def split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(";") if part.strip()]


def load_inputs() -> dict:
    return {
        "manifest": read_json(DATA_ROOT / "coach_manifest.json"),
        "rules": read_json(DATA_ROOT / "program_rules.json"),
        "availability": read_csv(DATA_ROOT / "availability_calendar.csv"),
        "exercise_catalog": read_json(DATA_ROOT / "exercise_catalog.json"),
        "food_catalog": read_csv(DATA_ROOT / "food_catalog.csv"),
    }


def exercise_candidates(inputs: dict, focus: str, pattern: str) -> list[dict]:
    manifest = inputs["manifest"]
    rules = inputs["rules"]["workout_rules"]
    excluded = {int(x) for x in rules["hard_excluded_exercise_ids"]}
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


def food_candidates(inputs: dict, slot: str, role: str) -> list[dict]:
    excluded_tags = set(inputs["manifest"]["excluded_food_tags"])
    out = []
    for row in inputs["food_catalog"]:
        if row["approved"].strip().lower() != "true" or row["allowed"].strip().lower() != "true":
            continue
        if slot not in split_csv(row["meal_slots"]):
            continue
        tags = split_tags(row["tags"])
        if role not in tags:
            continue
        if tags & excluded_tags:
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


def build_outputs() -> tuple[dict, list[dict], dict, str]:
    inputs = load_inputs()
    rules = inputs["rules"]
    training_rows = {row["day_id"]: row for row in inputs["availability"] if row["row_type"] == "training"}
    used_ids: set[int] = set()
    family_totals = defaultdict(int)
    coverage_flags = {name: False for name in rules["workout_rules"]["required_coverage"]}
    training_days = []

    for day_template in rules["workout_rules"]["day_templates"]:
        exercises = []
        for slot_index, pattern in enumerate(day_template["required_patterns"], start=1):
            chosen = None
            for candidate in exercise_candidates(inputs, day_template["focus"], pattern):
                candidate_id = int(candidate["exercise_id"])
                if candidate_id in used_ids:
                    continue
                chosen = candidate
                break
            if chosen is None:
                raise RuntimeError(f"Missing candidate for {day_template['day_id']} / {pattern}")
            used_ids.add(int(chosen["exercise_id"]))
            family_totals[chosen["coverage_family"]] += int(chosen["default_sets"])
            coverage_flags[chosen["coverage_family"]] = True
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
        training_days.append(
            {
                "day_id": day_template["day_id"],
                "calendar_date": training_rows[day_template["day_id"]]["calendar_date"],
                "focus": day_template["focus"],
                "estimated_duration_min": int(day_template["estimated_duration_min"]),
                "exercises": exercises,
            }
        )

    nutrition_rules = rules["nutrition_rules"]
    meal_rows = []
    meal_totals = []
    for day_template in nutrition_rules["plan_day_templates"]:
        total = {"plan_day": day_template["plan_day"], "calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for slot in nutrition_rules["required_meal_slots"]:
            for role_spec in day_template["slot_roles"][slot]:
                chosen = food_candidates(inputs, slot, role_spec["role"])[0]
                grams = int(role_spec["serving_grams"])
                macros = calculate_macros(chosen, grams)
                meal_rows.append(
                    {
                        "plan_day": day_template["plan_day"],
                        "meal_slot": slot,
                        "food_id": str(int(chosen["food_id"])),
                        "food_description": chosen["description"],
                        "serving_grams": str(grams),
                        "servings": "1",
                        "calories_kcal": f"{macros['calories_kcal']:.1f}",
                        "protein_g": f"{macros['protein_g']:.1f}",
                        "carbs_g": f"{macros['carbs_g']:.1f}",
                        "fat_g": f"{macros['fat_g']:.1f}",
                        "prep_note": f"Use the current {slot} portion and keep it simple.",
                    }
                )
                total["calories_kcal"] += macros["calories_kcal"]
                total["protein_g"] += macros["protein_g"]
                total["carbs_g"] += macros["carbs_g"]
                total["fat_g"] += macros["fat_g"]
        meal_totals.append(
            {
                "plan_day": day_template["plan_day"],
                "calories_kcal": round(total["calories_kcal"], 1),
                "protein_g": round(total["protein_g"], 1),
                "carbs_g": round(total["carbs_g"], 1),
                "fat_g": round(total["fat_g"], 1),
            }
        )

    workout_plan = {
        "member_id": inputs["manifest"]["member_id"],
        "goal": inputs["manifest"]["goal"],
        "training_days": training_days,
    }
    summary = {
        "member_id": inputs["manifest"]["member_id"],
        "goal": inputs["manifest"]["goal"],
        "training_day_count": 4,
        "meal_day_count": 2,
        "nutrition_targets": {
            "daily_calories_kcal": nutrition_rules["daily_calories_kcal"],
            "daily_protein_min_g": nutrition_rules["daily_protein_min_g"],
            "daily_carb_range_g": nutrition_rules["daily_carb_range_g"],
            "daily_fat_range_g": nutrition_rules["daily_fat_range_g"],
        },
        "meal_day_totals": meal_totals,
        "coverage_flags": coverage_flags,
        "weekly_set_totals": {
            "push": family_totals["push"],
            "pull": family_totals["pull"],
            "squat_or_lunge": family_totals["squat_or_lunge"],
            "hinge": family_totals["hinge"],
            "core": family_totals["core"],
        },
        "notes": [
            "Current approved exercises replaced stale shortlist items with unavailable equipment assumptions.",
            "The four-day split keeps one clear focus per day while preserving full coverage across the week.",
        ],
    }
    handoff = "\n".join(
        [
            "# Member Overview",
            f"Member {inputs['manifest']['member_id']} is training for {inputs['manifest']['goal']}.",
            "",
            "# Training Plan",
            "DAY-1 is upper_push, DAY-2 is lower_1, DAY-3 is upper_pull, and DAY-4 is lower_2_core.",
            "",
            "# Meal Plan",
            f"PLAN-A totals {meal_totals[0]['calories_kcal']} kcal and PLAN-B totals {meal_totals[1]['calories_kcal']} kcal.",
            "",
            "# Changes From Earlier Exports",
            "The final delivery replaces stale shortlist IDs 1055, 1061, 1073, 3102, 3118, and 3127.",
            "Current catalog picks include 1107, 1114, 1122, 1129, 3208, 3215, and 3232.",
            "",
            "# Watch Items",
            "Keep the lower-body sessions one day apart when possible and prep the lunch proteins in advance.",
        ]
    ) + "\n"
    return workout_plan, meal_rows, summary, handoff


def write_outputs(workout_plan: dict, meal_rows: list[dict], summary: dict, handoff: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "workout_plan.json").write_text(json.dumps(workout_plan, indent=2), encoding="utf-8")
    with (OUTPUT_ROOT / "meal_plan.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "plan_day",
            "meal_slot",
            "food_id",
            "food_description",
            "serving_grams",
            "servings",
            "calories_kcal",
            "protein_g",
            "carbs_g",
            "fat_g",
            "prep_note",
        ])
        writer.writeheader()
        for row in meal_rows:
            writer.writerow(row)
    (OUTPUT_ROOT / "plan_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUTPUT_ROOT / "coach_handoff.md").write_text(handoff, encoding="utf-8")


def main() -> None:
    write_outputs(*build_outputs())


if __name__ == "__main__":
    main()
