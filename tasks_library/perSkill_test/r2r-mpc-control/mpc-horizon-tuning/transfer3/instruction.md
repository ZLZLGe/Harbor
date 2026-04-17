You are tuning a predictive controller for a dual-winder pair under repeating reference cycles.

Input file:
- `/root/transfer3_winder_case.json`

For every candidate in `candidates`:
1. Build diagonal `Q` using `q_primary` for `primary_indices` and `q_secondary` for `secondary_indices`.
2. Build `R = r_scale * I`.
3. Build `Qf = terminal_weight_scale * Q`.
4. Compute finite-horizon gain using backward Riccati recursion.
5. Simulate all steps with clipped control.

State update:
`x_next = A @ x + B @ u + disturbance`

Reference is cyclic: select `cycle_pattern[(k // cycle_span) % len(cycle_pattern)]`.

Write:
1. `/root/transfer3_winder_trace.json`
2. `/root/transfer3_winder_tuning_report.json`

`/root/transfer3_winder_trace.json`:
- `scenario`: string
- `selected_candidate_id`: string
- `records`: one item per step
- each item contains:
  - `k` (integer)
  - `reference` (4 floats)
  - `state` (4 floats)
  - `control` (2 floats)

`/root/transfer3_winder_tuning_report.json`:
- `scenario`: string
- `best_candidate_id`: string
- `best_horizon`: integer
- `ranking`: sorted ascending by `score`, each item includes:
  - `candidate_id` (string)
  - `horizon` (integer)
  - `tracking_rmse` (float)
  - `control_rms` (float)
  - `control_delta_rms` (float)
  - `cycle_tail_mae` (float)
  - `score` (float)
- `weights`: object copied from input
- `trace_file`: string, exactly `/root/transfer3_winder_trace.json`

Rules:
1. Produce exactly `steps` records per candidate.
2. Apply per-channel clipping with `u_limit`.
3. `control_delta_rms` is RMS of step-to-step control differences.
4. `cycle_tail_mae` is MAE over primary indices in the final `tail_steps` records.
5. Score formula:
   `w_tracking*tracking_rmse + w_control*control_rms + w_delta*control_delta_rms + w_tail*cycle_tail_mae`
6. Select the minimum-score candidate.
