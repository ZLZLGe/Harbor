You are controlling a 4-zone industrial oven with persistent actuator bias during a staged recipe.

Input file:
- `/root/transfer1_oven_case.json`

Simulate the full horizon and apply the nominal correction from the case data, augmented by a bounded decayed error-memory term.

Write these files:
1. `/root/transfer1_oven_timeline.json`
2. `/root/transfer1_oven_balance_report.json`

`/root/transfer1_oven_timeline.json`:
- `records`: one item per step.
- Every item must contain:
  - `k` (integer)
  - `reference` (4 floats)
  - `temperature` (4 floats)
  - `u_nominal` (4 floats)
  - `integral` (4 floats)
  - `u_total` (4 floats)

`/root/transfer1_oven_balance_report.json`:
- `scenario`: string
- `controller`:
  - `gamma` (float)
  - `c_i` (4 floats)
  - `max_integral` (4 floats)
- `tail_mae_baseline` (float)
- `tail_mae_controlled` (float)
- `improvement_ratio` (float, defined as `1 - tail_mae_controlled / tail_mae_baseline`)
- `zone_peak_deviation` (4 floats)
- `integral_clip_count` (integer)
- `timeline_file` (string, exactly `/root/transfer1_oven_timeline.json`)

Rules:
1. Use the recipe schedule embedded in the input file.
2. Enforce integral bounds every step.
3. `records` length must match `steps`.
4. Compute metrics directly from generated simulation data.
