---
name: fitness-nutrition
description: Use the bundled builder and validator to produce the required strength-plan delivery from `/root/data` into `/root/output` when a task asks for workout, meal, summary, and handoff files.
---

# Fitness Nutrition

Use this skill when a task asks for a workout plan, meal plan, summary, and coach handoff built from `/root/data` with current catalogs and planning rules.

## First Path To Try

1. Run `python3 /root/.codex/skills/fitness-nutrition/scripts/build_delivery.py`
2. Run `python3 /root/.codex/skills/fitness-nutrition/scripts/validate_plan.py`
3. If step 2 prints `ok`, submit the generated files from `/root/output/` without reworking them by hand.

If `/root/.codex/skills/fitness-nutrition/` is unavailable, use the matching path under `/logs/agent/skills/fitness-nutrition/`.

## Why This Fast Path Matters

- The bundled scripts already apply the current exercise and food selection policy.
- They already write the required output schema and the required handoff sections.
- They already align the workout plan, meal plan, summary, and handoff with the same current inputs.

## If Validation Fails

1. Read `/root/data/coach_manifest.json`, `/root/data/program_rules.json`, and `/root/data/availability_calendar.csv`.
2. Confirm the generated files under `/root/output/` match the active catalogs under `/root/data/`.
3. Make the smallest possible adjustment outside any `skills` directory, then rerun the validator.

## Available Helpers

- `python3 /root/.codex/skills/fitness-nutrition/scripts/filter_exercises.py`
- `python3 /root/.codex/skills/fitness-nutrition/scripts/assemble_workout.py`
- `python3 /root/.codex/skills/fitness-nutrition/scripts/filter_foods.py`
- `python3 /root/.codex/skills/fitness-nutrition/scripts/assemble_meals.py`
- `python3 /root/.codex/skills/fitness-nutrition/scripts/build_delivery.py`
- `python3 /root/.codex/skills/fitness-nutrition/scripts/validate_plan.py`

## Notes

- Prefer current approved catalog items over earlier shortlist exports.
- Avoid rebuilding the full delivery manually unless the validator shows a concrete mismatch that needs investigation.
