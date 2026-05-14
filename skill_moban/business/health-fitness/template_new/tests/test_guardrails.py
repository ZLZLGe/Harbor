from __future__ import annotations

import subprocess
from pathlib import Path

from common import DATA_ROOT, HANDOFF_PATH, build_expected, load_meal_rows, load_summary, load_workout_plan


def test_current_only_exercise_ids_are_present() -> None:
    workout = load_workout_plan()
    chosen_ids = {exercise["exercise_id"] for day in workout["training_days"] for exercise in day["exercises"]}
    assert {1107, 1114, 1122, 1129}.issubset(chosen_ids), "Current-only exercise IDs are missing from the plan"


def test_stale_or_disallowed_ids_are_absent() -> None:
    workout = load_workout_plan()
    meal_rows = load_meal_rows()
    chosen_exercise_ids = {exercise["exercise_id"] for day in workout["training_days"] for exercise in day["exercises"]}
    chosen_food_ids = {int(row["food_id"]) for row in meal_rows}
    assert not ({1055, 1061, 1073} & chosen_exercise_ids), "Plan used stale or blocked exercise IDs"
    assert not ({3102, 3118, 3127} & chosen_food_ids), "Meal plan used stale or blocked food IDs"


def test_outputs_hit_macro_and_set_targets() -> None:
    summary = load_summary()
    expected = build_expected()["summary"]
    assert summary["weekly_set_totals"] == expected["weekly_set_totals"], "Weekly set totals do not match the required current plan"
    assert summary["meal_day_totals"] == expected["meal_day_totals"], "Meal totals do not match the current catalog calculations"


def test_handoff_calls_out_shortlist_replacements() -> None:
    text = HANDOFF_PATH.read_text(encoding="utf-8")
    assert "shortlist" in text.lower(), "Handoff must mention shortlist changes"
    assert "1055" in text and "3208" in text, "Handoff must mention both removed stale IDs and current replacements"


def test_inputs_were_not_modified() -> None:
    data_hash_path = Path("/opt/health-fitness-data.sha256")

    if data_hash_path.exists():
        current_data = subprocess.check_output(
            f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
            shell=True,
            text=True,
        )
        assert current_data == data_hash_path.read_text(encoding="utf-8"), "Input data under /root/data was modified"
