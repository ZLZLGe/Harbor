You are preparing a publishable 4-day training split and a 2-day repeatable meal plan for a new member at a neighborhood strength studio. The workspace already contains earlier shortlist exports, but they may be incomplete or outdated; for this delivery, the current exercise catalog, food catalog, schedule inputs, and program rules are the planning authority.

Input data is in `/root/data/`:

- `coach_manifest.json`: member profile, goal, available equipment, excluded food tags, and delivery requirements.
- `exercise_catalog.json`: current exercise catalog with approval status, equipment, movement pattern, focus compatibility, and default prescription fields.
- `food_catalog.csv`: current food catalog with approval status, allowed meal slots, macro values per 100 grams, and planning tags.
- `availability_calendar.csv`: training dates, duration limits, meal slots, and meal timing windows.
- `program_rules.json`: training coverage requirements, nutrition targets, selection policy, and handoff requirements.
- `exercise_shortlist.csv`: an earlier candidate exercise shortlist from a prior planning pass.
- `food_shortlist.csv`: an earlier candidate food shortlist from a prior planning pass.

Your task

1. Review the current planning inputs and select compliant exercises for each training day.
2. Build a 4-day training split that satisfies equipment limits, movement coverage, schedule constraints, and program rules.
3. Build a 2-day repeatable meal plan that satisfies the calorie and macro guardrails using only currently allowed foods.
4. Produce a coach-ready summary and handoff that match the final plan.
5. When more than one approved option fits a required slot, apply the current selection policy from `program_rules.json` exactly.

Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/workout_plan.json`

Top-level structure must be exactly:

```json
{
  "member_id": "MEM-001",
  "goal": "build_strength_and_muscle",
  "training_days": [
    {
      "day_id": "DAY-1",
      "calendar_date": "2026-06-08",
      "focus": "upper_push",
      "estimated_duration_min": 58,
      "exercises": [
        {
          "slot": 1,
          "exercise_id": 1001,
          "exercise_name": "Barbell Bench Press",
          "sets": 4,
          "reps": "6-8",
          "rest_sec": 150,
          "equipment": "barbell",
          "primary_muscles": ["Pectoralis major", "Triceps brachii"],
          "coach_note": "Control the eccentric and finish one rep shy of failure."
        }
      ]
    }
  ]
}
```

Requirements:

- Include exactly 4 objects in `training_days`.
- Every required training day must appear exactly once.
- Each training day must contain exactly 4 exercises.
- Every `exercise_id` must resolve to the current approved exercise catalog.
- Use only equipment currently available to the member.
- The final split must satisfy the movement coverage and weekly set guardrails in the current program rules.
- `coach_note` must be short and actionable.

2. Write `/root/output/meal_plan.csv`

Column names must be exactly:

```csv
plan_day,meal_slot,food_id,food_description,serving_grams,servings,calories_kcal,protein_g,carbs_g,fat_g,prep_note
```

Requirements:

- Include exactly 2 plan days.
- Across the CSV rows for each `plan_day`, use exactly these meal slots: `breakfast`, `lunch`, `dinner`, `snack`.
- Every `food_id` must resolve to the current approved food catalog.
- Use only foods that are currently allowed for the member and currently available in the planning inputs.
- `serving_grams` must be an integer.
- `calories_kcal`, `protein_g`, `carbs_g`, and `fat_g` must match the current food data for the chosen serving size.
- Each plan day must satisfy the calorie and macro guardrails in the current program rules.
- `prep_note` must be short and practical.

3. Write `/root/output/plan_summary.json`

Top-level structure must be exactly:

```json
{
  "member_id": "MEM-001",
  "goal": "build_strength_and_muscle",
  "training_day_count": 4,
  "meal_day_count": 2,
  "nutrition_targets": {
    "daily_calories_kcal": [2300, 2400],
    "daily_protein_min_g": 190,
    "daily_carb_range_g": [210, 250],
    "daily_fat_range_g": [60, 85]
  },
  "meal_day_totals": [
    {
      "plan_day": "PLAN-A",
      "calories_kcal": 2354.6,
      "protein_g": 196.9,
      "carbs_g": 244.7,
      "fat_g": 66.6
    }
  ],
  "coverage_flags": {
    "push": true,
    "pull": true,
    "squat_or_lunge": true,
    "hinge": true,
    "core": true
  },
  "weekly_set_totals": {
    "push": 10,
    "pull": 13,
    "squat_or_lunge": 10,
    "hinge": 7,
    "core": 12
  },
  "notes": [
    "Example note"
  ]
}
```

Requirements:

- `training_day_count` must be `4`.
- `meal_day_count` must be `2`.
- `nutrition_targets` must match the current planning inputs.
- `meal_day_totals` must contain exactly 2 objects, one for each plan day.
- `coverage_flags` and `weekly_set_totals` must reflect the final workout plan.
- `notes` must contain at least 2 brief planning notes.

4. Write `/root/output/coach_handoff.md`

It must contain these H1 headings in this order:

- `# Member Overview`
- `# Training Plan`
- `# Meal Plan`
- `# Changes From Earlier Exports`
- `# Watch Items`

Requirements:

- Summarize the member goal, main constraints, and final training split.
- Call out exercise or food selections that changed from the earlier shortlists.
- Mention schedule or prep tradeoffs that affected the final plan.
- Include any remaining watch items for the coach.

Notes:

- `exercise_shortlist.csv` and `food_shortlist.csv` are background references only and may not match the current planning state.
- If multiple current options remain valid for the same required slot, the current selection policy is the tie-break authority.
- Do not edit files under `/root/data/`.
- Do not invent exercises, foods, serving sizes, equipment, or rule thresholds.
- Do not bypass current planning inputs, hardcode final outputs, or reduce scope by dropping required training days or meal days.
- Do not modify tests, verifier files, task metadata, environment files, or other preinstalled reference materials.
- You may write helper scripts in the workspace, but the final submission only needs the required files under `/root/output/`.
