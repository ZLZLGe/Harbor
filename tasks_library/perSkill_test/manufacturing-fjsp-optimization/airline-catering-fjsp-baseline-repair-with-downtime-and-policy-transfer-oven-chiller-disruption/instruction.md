You are repairing a central-kitchen baseline for outbound airline catering. Each flight meal lot must go through `prep -> cook -> chill -> assemble`. The published shift plan is no longer executable because one oven bank and one blast-chiller line enter maintenance. Using only the assets under `/app/data/`, write the repaired shift plan to `/app/output/catering_shift_plan.json`.

Available input files:

- `/app/data/flight_service_manifest.json`: flight departures, ready-buffer targets, equipment catalog, and the allowed equipment options with durations for each stage.
- `/app/data/equipment_maintenance.csv`: maintenance windows for ovens and blast chillers.
- `/app/data/repair_policy.json`: freeze rules, change-budget limits, and dispatch guardrails.
- `/app/data/baseline_catering_plan.json`: the published baseline in the same schema as the target output.
- `/app/data/baseline_risk_report.csv`: summary metrics for the baseline conflicts.

Requirements:

- Every `(flight_id, stage_index)` must appear exactly once.
- `finish = start + duration`, and `duration` must match the selected equipment option from `flight_service_manifest.json`.
- Each flight must preserve the stage order `prep -> cook -> chill -> assemble`.
- Jobs on the same `equipment_id` cannot overlap.
- No planned interval may overlap a maintenance window for the same `equipment_id`.
- Repairs are right-shift only: no row may start earlier than in the baseline.
- If a baseline row starts before `freeze.before_minute`, every field listed in `freeze.fields` must remain unchanged.
- The total number of equipment changes and the total start-time shift must stay within the policy budget.
- Each flight must finish its `assemble` stage no later than `departure_minute - ready_buffer`.
- `dispatch_board` must contain one row per flight, sorted by `(departure_minute, flight_id)`.

Output JSON format:

```json
{
  "status": "DISPATCHABLE",
  "last_ready_minute": 0,
  "budget_usage": {
    "equipment_changes": 0,
    "total_start_shift": 0
  },
  "dispatch_board": [
    {
      "flight_id": "HX215",
      "ready_minute": 0,
      "departure_minute": 180,
      "buffer_to_departure": 0
    }
  ],
  "kitchen_plan": [
    {
      "flight_id": "HX215",
      "stage": "prep",
      "stage_index": 0,
      "equipment_group": "prep",
      "equipment_id": "prep-a",
      "equipment_name": "Prep Bench A",
      "start": 0,
      "finish": 0,
      "duration": 0
    }
  ]
}
```

`last_ready_minute` is the maximum `finish` across all rows. `budget_usage` must match the repaired plan exactly. Every `dispatch_board` row must use the actual `assemble` finish as `ready_minute`, and `buffer_to_departure = departure_minute - ready_minute`.
