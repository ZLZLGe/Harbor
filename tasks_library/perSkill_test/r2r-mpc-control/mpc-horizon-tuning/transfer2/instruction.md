You are tuning predictive-control settings for a coupled 3-reservoir network with soft safety limits.

Input file:
- `/root/transfer2_reservoir_case.json`

For each candidate in `candidates`:
1. Build `Q` diagonal using `q_primary` on `primary_indices` and `q_secondary` on `secondary_indices`.
2. Build `R = r_scale * I`.
3. Build terminal matrix `Qf = terminal_weight_scale * Q`.
4. Compute finite-horizon gain using backward Riccati recursion with the candidate horizon.
5. Simulate all steps with clipped control and additive disturbance.

State update:
`x_next = A @ x + B @ u + disturbance`

Reference is piecewise constant from `reference_schedule`.

Write:
1. `/root/transfer2_reservoir_trace.json`
2. `/root/transfer2_reservoir_horizon_report.json`

`/root/transfer2_reservoir_trace.json`:
- `scenario`: string
- `selected_candidate_id`: string
- `records`: one item per step
- every item contains:
  - `k` (integer)
  - `reference` (6 floats)
  - `state` (6 floats)
  - `control` (3 floats)

`/root/transfer2_reservoir_horizon_report.json`:
- `scenario`: string
- `best_candidate_id`: string
- `best_horizon`: integer
- `ranking`: ascending by `score`, each item includes:
  - `candidate_id` (string)
  - `horizon` (integer)
  - `tracking_rmse` (float)
  - `control_rms` (float)
  - `overflow_risk` (float)
  - `settling_fraction` (float)
  - `score` (float)
- `weights`: object copied from input
- `trace_file`: string, exactly `/root/transfer2_reservoir_trace.json`

Rules:
1. Produce exactly `steps` records for each candidate.
2. Apply control clipping using `u_limit`.
3. `overflow_risk` is the maximum positive exceedance over `safe_primary_max` for primary indices.
4. `settling_fraction = settling_step / steps`, where `settling_step` is searched from the final schedule change and requires all primary absolute errors <= `settling_tol` through the end.
5. Score formula:
   `w_tracking*tracking_rmse + w_control*control_rms + w_overflow*overflow_risk + w_settling*settling_fraction`
6. Select the minimum-score candidate.
