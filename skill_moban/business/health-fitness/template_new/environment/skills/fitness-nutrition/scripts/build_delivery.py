from __future__ import annotations

import csv
import json
from pathlib import Path

from planner_core import OUTPUT_ROOT, build_handoff, build_meal_plan, build_workout_plan, load_inputs


def main() -> None:
    inputs = load_inputs()
    workout, summary = build_workout_plan(inputs)
    meal_rows, meal_totals = build_meal_plan(inputs)
    summary["meal_day_totals"] = meal_totals
    handoff = build_handoff(inputs, {"training_days": workout["training_days"], "summary": summary}, meal_totals)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "workout_plan.json").write_text(json.dumps(workout, indent=2), encoding="utf-8")
    with (OUTPUT_ROOT / "meal_plan.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        for row in meal_rows:
            writer.writerow(row)
    (OUTPUT_ROOT / "plan_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUTPUT_ROOT / "coach_handoff.md").write_text(handoff, encoding="utf-8")


if __name__ == "__main__":
    main()
