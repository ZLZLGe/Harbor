You are repairing a baseline flexible job shop schedule for a beverage bottling campaign. Six SKU batches move through three stages: bottle prep, fill-cap, and case pack. The current baseline collides with sanitation and CIP downtime windows, while the earliest promotional batches are frozen on locked fields and cannot be altered there.

Input files are stored in `/app/data/`:
- `instance.txt`: flexible job shop instance in the compact standard format.
- `downtime.csv`: sanitation, CIP, or allergen flush downtime windows for each machine.
- `policy.json`: freeze rules plus machine-change and total start-shift budgets.
- `baseline_solution.json`: the current baseline schedule.
- `baseline_metrics.json`: summary metrics for the baseline.

Produce a repaired schedule that is feasible for the bottling campaign and stays within the approved change budget. Respect these rules:
- Preserve the same `(job, op)` set as the baseline.
- Never start an operation earlier than its baseline start.
- Respect job precedence for every batch.
- Avoid all machine overlaps and all downtime windows.
- Use only legal machine and duration pairs from `instance.txt`.
- Respect the freeze window and locked fields from `policy.json`.
- Keep machine changes and total L1 start-time shift within the budget in `policy.json`.

Write both of the following files:

`/app/output/solution.json`
```json
{
  "status": "FEASIBLE",
  "makespan": 0,
  "schedule": [
    {
      "job": 0,
      "op": 0,
      "machine": 0,
      "start": 0,
      "end": 0,
      "dur": 0
    }
  ]
}
```

`/app/output/schedule.csv`
- Must contain the exact same rows as `solution.json`.
- Required columns: `job,op,machine,start,end,dur`.
