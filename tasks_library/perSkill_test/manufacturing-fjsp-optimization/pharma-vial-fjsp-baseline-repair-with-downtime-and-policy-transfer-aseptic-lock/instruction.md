You are repairing a baseline flexible job shop schedule for an aseptic vial filling campaign. Five sterile batches move through fill, crimp, and visual inspection. The baseline collides with cleaning downtime, and early released batches are frozen on selected fields.

Input files are stored in `/app/data/`:
- `instance.txt`: legal machine and duration choices for every `(job, op)`.
- `downtime.csv`: clean-in-place or sterility-hold downtime windows.
- `policy.json`: freeze rules plus `change_budget.max_machine_changes` and `change_budget.max_total_start_shift_L1`.
- `baseline_solution.json`: the baseline schedule to repair. Its row order is the baseline row order referenced below.
- `baseline_metrics.json`: baseline summary metrics.

Your repaired schedule must satisfy all of the following:
- Preserve exactly the same `(job, op)` set as the baseline.
- Use only legal machine and duration pairs from `instance.txt`.
- Never start an operation earlier than its baseline start.
- Respect job precedence.
- Avoid all machine overlaps and all downtime windows.
- Read `freeze.until` and `freeze.fields` from `policy.json`.
- For any baseline row whose `start < freeze.until`, keep every field listed in `freeze.fields` unchanged from the baseline row.
- Keep machine changes and total L1 start-time shift within the budget in `policy.json`.
- Reduce downtime violations to zero.

Use this deterministic repair rule:
- Process operations in the order obtained by sorting baseline rows by `(op, baseline start, baseline row order in baseline_solution.json)`.
- For each operation, let `anchor = max(baseline start, end of the previous operation in the same job)`.
- After choosing a machine, schedule that operation at the earliest feasible start time `>= anchor` that does not overlap already scheduled work on that machine and does not overlap downtime on that machine.

Optimization target:
- Among all schedules that satisfy the rules above, choose one with lexicographically minimum `(makespan, machine_changes, total_l1_start_shift)`.
- If multiple schedules still tie, sort their rows by `(start, job, op)` and choose the lexicographically smallest row list when each row is represented as `(job, op, machine, start, end, dur)`.

Write both outputs with rows sorted by `(start, job, op)`:

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
- `status` must be `"FEASIBLE"`.
- `makespan` must equal the maximum `end` value in `schedule`.

`/app/output/schedule.csv`
- Must contain the same rows, in the same order, as `solution.json`.
- Required columns: `job,op,machine,start,end,dur`.
