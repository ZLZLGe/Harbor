You are coordinating a small airport ground-traffic planning batch.

The batch manifest is stored at `/root/airport_batch.json`. Each entry gives you:
1. A PDDL domain file path.
2. A PDDL problem file path.
3. The required output path for the plan file.

For every case in the manifest:
1. Load the listed PDDL domain and PDDL problem.
2. Generate a valid sequential plan that solves the case.
3. Write the plan to the exact `plan_output` path listed in the manifest.

After all plan files are written, create `/root/similar_airport_manifest.json`.

Write the manifest as JSON with this shape:

```json
{
  "scenario": "airport_dispatch",
  "cases": [
    {
      "case_id": "ground_alpha",
      "plan_file": "/root/airport_plans/ground_alpha.plan",
      "action_count": 12,
      "first_action": "...",
      "last_action": "..."
    }
  ]
}
```

Rules:
1. Sort the `cases` array by `case_id` ascending.
2. `plan_file` must exactly match the plan path for that case.
3. `action_count` must equal the number of non-empty plan action lines in the plan file.
4. `first_action` must be the first non-empty action line in the plan file.
5. `last_action` must be the last non-empty action line in the plan file.
6. Every generated plan must be syntactically valid and solve its listed PDDL problem.
