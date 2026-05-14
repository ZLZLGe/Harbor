from __future__ import annotations

import csv
import json
import sys

from planner_core import build_meal_plan, load_inputs


def main() -> None:
    inputs = load_inputs()
    rows, totals = build_meal_plan(inputs)
    writer = csv.DictWriter(
        sys.stdout,
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
    for row in rows:
        writer.writerow(row)
    print(json.dumps({"totals": totals}, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
