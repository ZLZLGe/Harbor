You are tuning a predictive controller for a six-state roll-to-roll line surrogate under a step change.

Input file:
- `/root/similar_mpc_case.json`

Evaluate every candidate listed in `candidates` and simulate each one over the full horizon.
For candidate `c`:
1. Build `Q` as a diagonal matrix:
   - indices in `primary_indices` use `c.q_primary`
   - indices in `secondary_indices` use `c.q_secondary`
2. Build `R = c.r_scale * I`.
3. Build terminal cost `Qf = terminal_weight_scale * Q`.
4. Compute a finite-horizon LQR gain using backward Riccati recursion with `horizon = c.horizon`.
5. Run closed-loop simulation using the first-step gain and clipped control.

State update per step:
`x_next = A @ x + B @ u + disturbance`

Reference is piecewise constant from `reference_schedule`.

Write these files:
1. `/root/similar_horizon_trace.json`
2. `/root/similar_horizon_report.json`

`/root/similar_horizon_trace.json`:
- `scenario`: string
- `selected_candidate_id`: string
- `records`: array with one item per step
- each record must include:
  - `k` (integer)
  - `reference` (6 floats)
  - `state` (6 floats)
  - `control` (3 floats)

`/root/similar_horizon_report.json`:
- `scenario`: string
- `best_candidate_id`: string
- `best_horizon`: integer
- `ranking`: array sorted by ascending `score`, each item includes:
  - `candidate_id` (string)
  - `horizon` (integer)
  - `tracking_rmse` (float)
  - `control_rms` (float)
  - `overshoot_primary` (float)
  - `settling_fraction` (float)
  - `score` (float)
- `weights`: object copied from input `weights`
- `trace_file`: string, exactly `/root/similar_horizon_trace.json`

Rules:
1. Simulate exactly `steps` records for every candidate.
2. Enforce per-channel control clipping using `u_limit`.
3. `settling_fraction` = `settling_step / steps`, where `settling_step` is the first step after the step change where all primary-index errors remain within `settling_tol` for the rest of the run.
4. Score each candidate as:
   `w_tracking*tracking_rmse + w_control*control_rms + w_overshoot*overshoot_primary + w_settling*settling_fraction`
5. Select the candidate with the lowest score.
