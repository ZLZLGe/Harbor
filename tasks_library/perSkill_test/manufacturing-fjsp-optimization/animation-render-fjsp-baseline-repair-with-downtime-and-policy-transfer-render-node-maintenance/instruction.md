You are repairing a published animation render-farm queue for the next review session. Every shot must pass `prep -> render -> composite -> qc`. The current queue is no longer executable because some render nodes and comp suites enter maintenance. Using only the assets under `/app/data/`, write the recovered plan to `/app/output/render_recovery_plan.json`.

Available input files:

- `/app/data/show_manifest.json`: shot deadlines, station catalog, and the allowed station options with durations for each stage.
- `/app/data/maintenance_windows.csv`: maintenance windows for render nodes and comp suites.
- `/app/data/recovery_policy.json`: freeze rules, change-budget limits, and review guardrails.
- `/app/data/baseline_render_queue.csv`: the published baseline queue in row form.
- `/app/data/baseline_health.json`: baseline maintenance impact summary for comparison.

Requirements:

- Every `(shot_id, stage_index)` must appear exactly once.
- `finish = start + duration`, and `duration` must match the selected station option from `show_manifest.json`.
- Each shot must preserve the stage order `prep -> render -> composite -> qc`.
- Tasks on the same `station_id` cannot overlap.
- No planned interval may overlap a maintenance window for the same `station_id`.
- Repairs are right-shift only: no row may start earlier than in the baseline.
- If a baseline row starts before `freeze.before_minute`, every field listed in `freeze.fields` must remain unchanged.
- The total number of station changes and the total start-time shift must stay within the policy budget.
- Every shot must finish its `qc` stage by its `review_due`.
- `review_queue` must list shot IDs in ascending order of actual `qc` finish time, breaking ties by `shot_id`.

Output JSON format:

```json
{
  "status": "READY_FOR_REVIEW",
  "last_review_minute": 0,
  "budget_usage": {
    "station_changes": 0,
    "total_start_shift": 0
  },
  "review_queue": [
    "SH010"
  ],
  "render_plan": [
    {
      "shot_id": "SH010",
      "stage": "prep",
      "stage_index": 0,
      "station_id": "prep-b",
      "station_name": "Prep Bay B",
      "start": 0,
      "finish": 0,
      "duration": 0
    }
  ]
}
```

`last_review_minute` is the maximum `finish` across all rows. `budget_usage` must match the recovered plan exactly.
