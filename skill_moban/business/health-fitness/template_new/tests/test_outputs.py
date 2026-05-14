from __future__ import annotations

from collections import defaultdict

from common import (
    HANDOFF_PATH,
    MEAL_FIELDS,
    MEAL_PATH,
    SUMMARY_PATH,
    WORKOUT_PATH,
    build_expected,
    calculate_macros,
    exercise_map,
    food_map,
    is_truthy,
    load_inputs,
    load_meal_rows,
    load_summary,
    load_workout_plan,
    meal_totals_from_rows,
    template_lookup,
    training_lookup,
    workout_metrics_from_plan,
)


def test_required_output_files_exist() -> None:
    assert WORKOUT_PATH.exists(), "Missing /root/output/workout_plan.json"
    assert MEAL_PATH.exists(), "Missing /root/output/meal_plan.csv"
    assert SUMMARY_PATH.exists(), "Missing /root/output/plan_summary.json"
    assert HANDOFF_PATH.exists(), "Missing /root/output/coach_handoff.md"


def test_workout_plan_matches_current_constraints() -> None:
    inputs = load_inputs()
    manifest = inputs["manifest"]
    day_templates = template_lookup(inputs)
    training_days = training_lookup(inputs)
    catalog = exercise_map(inputs)
    rules = inputs["rules"]["workout_rules"]
    expected = build_expected()["workout_plan"]
    expected_days = {day["day_id"]: day for day in expected["training_days"]}
    actual = load_workout_plan()
    assert actual["member_id"] == manifest["member_id"]
    assert actual["goal"] == manifest["goal"]
    assert len(actual["training_days"]) == len(day_templates)
    assert {day["day_id"] for day in actual["training_days"]} == set(manifest["training_days"])

    used_ids: set[int] = set()
    for actual_day in actual["training_days"]:
        template = day_templates[actual_day["day_id"]]
        schedule_row = training_days[actual_day["day_id"]]
        expected_day = expected_days[actual_day["day_id"]]
        assert actual_day["calendar_date"] == schedule_row["calendar_date"]
        assert actual_day["focus"] == template["focus"]
        assert int(actual_day["estimated_duration_min"]) <= int(schedule_row["max_duration_min"])
        assert len(actual_day["exercises"]) == rules["max_exercises_per_day"]

        for slot_index, exercise in enumerate(actual_day["exercises"], start=1):
            exercise_id = int(exercise["exercise_id"])
            expected_exercise = expected_day["exercises"][slot_index - 1]
            assert exercise["slot"] == slot_index
            assert exercise_id not in used_ids, f"Exercise {exercise_id} was reused across days"
            used_ids.add(exercise_id)
            assert exercise_id in catalog, f"Exercise {exercise_id} is not in the current catalog"

            catalog_row = catalog[exercise_id]
            assert is_truthy(catalog_row["approved"])
            assert is_truthy(catalog_row["studio_available"])
            assert exercise_id not in set(rules["hard_excluded_exercise_ids"])
            assert catalog_row["equipment"] in set(manifest["equipment_available"])
            assert actual_day["focus"] in catalog_row["allowed_day_focuses"]
            assert catalog_row["movement_pattern"] == template["required_patterns"][slot_index - 1]
            assert exercise_id == expected_exercise["exercise_id"], f"Unexpected exercise choice for {actual_day['day_id']} slot {slot_index}"

            assert exercise["exercise_name"] == catalog_row["name"]
            assert int(exercise["sets"]) == int(catalog_row["default_sets"])
            assert exercise["reps"] == catalog_row["default_reps"]
            assert int(exercise["rest_sec"]) == int(catalog_row["default_rest_sec"])
            assert exercise["equipment"] == catalog_row["equipment"]
            assert exercise["primary_muscles"] == catalog_row["primary_muscles"]
            assert len(exercise["coach_note"].strip()) >= 8


def test_meal_plan_matches_current_food_data() -> None:
    inputs = load_inputs()
    manifest = inputs["manifest"]
    rules = inputs["rules"]["nutrition_rules"]
    catalog = food_map(inputs)
    expected_rows = build_expected()["meal_rows"]
    actual_rows = load_meal_rows()
    rows_by_day: dict[str, list[dict]] = defaultdict(list)

    assert len(actual_rows) == len(expected_rows), "Unexpected number of meal rows"
    for actual_row, expected_row in zip(actual_rows, expected_rows):
        assert list(actual_row.keys()) == MEAL_FIELDS, "Meal CSV header mismatch"
        plan_day = actual_row["plan_day"]
        meal_slot = actual_row["meal_slot"]
        rows_by_day[plan_day].append(actual_row)

        food_id = int(actual_row["food_id"])
        assert food_id in catalog, f"Food {food_id} is not in the current catalog"
        catalog_row = catalog[food_id]
        assert is_truthy(catalog_row["approved"])
        assert is_truthy(catalog_row["allowed"])
        assert meal_slot in catalog_row["meal_slots"].split(";")
        assert not (set(manifest["excluded_food_tags"]) & set(catalog_row["tags"].split(";")))
        assert actual_row["food_description"] == catalog_row["description"]

        grams = int(actual_row["serving_grams"])
        assert grams > 0
        assert int(actual_row["servings"]) == 1
        expected_macros = calculate_macros(catalog_row, grams)
        assert float(actual_row["calories_kcal"]) == expected_macros["calories_kcal"]
        assert float(actual_row["protein_g"]) == expected_macros["protein_g"]
        assert float(actual_row["carbs_g"]) == expected_macros["carbs_g"]
        assert float(actual_row["fat_g"]) == expected_macros["fat_g"]
        for field in ["plan_day", "meal_slot", "food_id", "food_description", "serving_grams", "servings"]:
            assert actual_row[field] == expected_row[field], f"Unexpected meal selection for {expected_row['plan_day']} {expected_row['meal_slot']}"
        assert len(actual_row["prep_note"].strip()) >= 8

    assert set(rows_by_day) == set(manifest["meal_days"])
    required_slots = set(rules["required_meal_slots"])
    for plan_day, rows in rows_by_day.items():
        assert {row["meal_slot"] for row in rows} == required_slots, f"Meal slots incomplete for {plan_day}"


def test_summary_matches_recomputed_totals_and_flags() -> None:
    inputs = load_inputs()
    rules = inputs["rules"]
    actual = load_summary()
    workout = load_workout_plan()
    meal_rows = load_meal_rows()
    expected_coverage, expected_weekly_sets = workout_metrics_from_plan(workout, inputs)
    expected_meal_totals = meal_totals_from_rows(meal_rows)

    assert actual["member_id"] == inputs["manifest"]["member_id"]
    assert actual["goal"] == inputs["manifest"]["goal"]
    assert actual["training_day_count"] == len(inputs["manifest"]["training_days"])
    assert actual["meal_day_count"] == len(inputs["manifest"]["meal_days"])
    assert actual["nutrition_targets"] == {
        "daily_calories_kcal": rules["nutrition_rules"]["daily_calories_kcal"],
        "daily_protein_min_g": rules["nutrition_rules"]["daily_protein_min_g"],
        "daily_carb_range_g": rules["nutrition_rules"]["daily_carb_range_g"],
        "daily_fat_range_g": rules["nutrition_rules"]["daily_fat_range_g"],
    }
    assert actual["coverage_flags"] == expected_coverage
    assert actual["weekly_set_totals"] == expected_weekly_sets
    assert actual["meal_day_totals"] == expected_meal_totals
    assert len(actual["notes"]) >= 2


def test_handoff_contains_required_sections_and_facts() -> None:
    expected = build_expected()
    text = HANDOFF_PATH.read_text(encoding="utf-8")
    headings = [
        "# Member Overview",
        "# Training Plan",
        "# Meal Plan",
        "# Changes From Earlier Exports",
        "# Watch Items",
    ]
    cursor = 0
    for heading in headings:
        next_cursor = text.find(heading, cursor)
        assert next_cursor >= 0, f"Missing heading {heading}"
        cursor = next_cursor + len(heading)
    assert expected["workout_plan"]["member_id"] in text
    assert expected["workout_plan"]["goal"] in text
    for token in expected["handoff_expected_tokens"]["replaced_ids"]:
        assert token in text, f"Handoff missing stale ID {token}"
    for token in expected["handoff_expected_tokens"]["current_ids"]:
        assert token in text, f"Handoff missing current ID {token}"
    assert any(keyword in text.lower() for keyword in ["schedule", "prep"]), "Handoff must mention a schedule or prep tradeoff"
