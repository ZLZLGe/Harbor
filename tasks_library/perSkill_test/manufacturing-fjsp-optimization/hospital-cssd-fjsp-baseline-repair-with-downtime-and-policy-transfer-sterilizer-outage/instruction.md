You are repairing a same-day CSSD reprocessing baseline for surgical instrument trays. Each tray must go through wash, inspect-pack, and sterilize steps. The published baseline is no longer executable because several washer and sterilizer outage windows invalidate it. Using only the assets under `/app/data/`, write a repaired day plan to `/app/output/cssd_day_plan.json`.

Available input files:

- `/app/data/tray_routes.json`: tray metadata, release deadlines, unit catalog, and the allowed units with durations for each step.
- `/app/data/unit_downtime.csv`: outage windows for washers, packing benches, and sterilizers.
- `/app/data/repair_policy.json`: freeze window, change-budget limits, and end-of-day guardrails.
- `/app/data/baseline_cssd_plan.json`: the current baseline day plan in the same schema as the target output.
- `/app/data/baseline_issues.json`: a summary of the known outage and overlap problems in the baseline.

Requirements:

- Every `(tray_id, step_index)` must appear exactly once.
- `finish = start + duration`, and `duration` must match the selected unit option from `tray_routes.json`.
- Each tray must preserve the step order `wash -> inspect_pack -> sterilize`.
- Jobs on the same `unit_id` cannot overlap.
- No planned interval may overlap an outage window for the same `unit_id`.
- Repairs are right-shift only: no step may start earlier than in the baseline.
- If a baseline row starts before the freeze horizon, all fields listed in the freeze policy must stay unchanged.
- The total number of unit changes and the total start-time shift must stay within the policy budget.
- Every tray must finish its sterilize step by its `release_deadline`.
- `ready_trays` must list tray IDs in ascending order of actual sterilize finish time, breaking ties by `tray_id`.

Output JSON format:

```json
{
  "status": "DAY_PLAN_READY",
  "last_ready_minute": 0,
  "budget_usage": {
    "unit_changes": 0,
    "total_start_shift": 0
  },
  "ready_trays": [
    "ER-TRAUMA-SET"
  ],
  "tray_plan": [
    {
      "tray_id": "ER-TRAUMA-SET",
      "step": "wash",
      "step_index": 0,
      "unit_id": 0,
      "unit_name": "Washer-A",
      "start": 0,
      "finish": 0,
      "duration": 0
    }
  ]
}
```

`last_ready_minute` is the maximum `finish` across all rows. `budget_usage` must match the repaired plan exactly.
