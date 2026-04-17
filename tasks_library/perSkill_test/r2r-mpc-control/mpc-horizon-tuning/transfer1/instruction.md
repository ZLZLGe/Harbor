You are tuning a predictive controller for a 4-zone thermal line with staged recipe targets.

Input file:
- `/root/transfer1_thermal_case.json`

Evaluate every candidate from `candidates`.
For each candidate:
1. Build diagonal `Q`:
   - indices in `primary_indices` use `q_primary`
   - indices in `secondary_indices` use `q_secondary`
2. Build `R = r_scale * I`.
3. Build `Qf = terminal_weight_scale * Q`.
4. Compute finite-horizon gain via backward Riccati recursion with the candidate horizon.
5. Simulate all steps with clipped control.

Dynamics each step:
`x_next = A @ x + B @ u + disturbance`

Reference is piecewise constant from `reference_schedule`.

Write:
1. `/root/transfer1_thermal_trace.json`
2. `/root/transfer1_thermal_tuning_report.json`

`/root/transfer1_thermal_trace.json`:
- `scenario`: string
- `selected_candidate_id`: string
- `records`: array, one entry per step
- each entry has:
  - `k` (integer)
  - `reference` (8 floats)
  - `state` (8 floats)
  - `control` (4 floats)

`/root/transfer1_thermal_tuning_report.json`:
- `scenario`: string
- `best_candidate_id`: string
- `best_horizon`: integer
- `ranking`: sorted ascending by `score`; each item includes:
  - `candidate_id` (string)
  - `horizon` (integer)
  - `tracking_rmse` (float)
  - `control_rms` (float)
  - `peak_primary_error` (float)
  - `settling_fraction` (float)
  - `score` (float)
- `weights`: object copied from input
- `trace_file`: string, exactly `/root/transfer1_thermal_trace.json`

Rules:
1. Every candidate must produce exactly `steps` records.
2. Apply per-channel control clipping with `u_limit` each step.
3. `settling_fraction = settling_step / steps`, where `settling_step` is searched from the final schedule change step and requires all primary-index absolute errors to stay <= `settling_tol` to the end.
4. Score formula:
   `w_tracking*tracking_rmse + w_control*control_rms + w_peak*peak_primary_error + w_settling*settling_fraction`
5. Select minimum-score candidate.
