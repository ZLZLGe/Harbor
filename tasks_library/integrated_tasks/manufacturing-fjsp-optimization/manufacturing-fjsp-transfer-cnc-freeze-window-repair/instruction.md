In a CNC machining cell, planners issued a baseline flexible job shop schedule before several maintenance windows were confirmed. Operations released before the freeze horizon must keep their locked fields exactly as published, while later operations may be delayed or moved to alternate eligible machines if needed. Your task is to repair the baseline into a downtime-feasible recovery plan that still respects job precedence and stays within the allowed machine-change and total start-shift budgets.

The input files are stored under `/app/data/`:
- `cnc_instance.txt`: flexible job shop instance with alternative machines and processing times
- `maintenance_windows.csv`: machine outage windows
- `recovery_policy.json`: freeze-window rules and policy budgets
- `baseline_cnc_plan.json`: baseline schedule to repair
- `baseline_metrics.json`: baseline reference metrics

Generate `/app/output/cnc_recovery_plan.json` with this schema:

```json
{
  "status": "",
  "makespan": 0,
  "machine_changes": 0,
  "total_start_shift": 0,
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

Also generate `/app/output/cnc_recovery_plan.csv` with the exact same schedule rows and columns: `job, op, machine, start, end, dur`.

Requirements:
- Keep every `(job, op)` from the baseline exactly once.
- Respect precedence for each job.
- Do not start any operation earlier than its baseline start time.
- Never overlap another operation on the same machine or any maintenance window.
- For operations whose baseline start is earlier than the freeze horizon, preserve every locked field declared in `recovery_policy.json`.
- Keep the final machine-change count and total L1 start-time shift within the policy budget.
