You are given a linear control case for a 6-section roll-to-roll tension line.

Input file:
- `/root/similar_case.json`

Build a finite-horizon LQR policy from the provided model and penalties.
Use terminal weight `P_N = Q` and run backward Riccati recursion for `k = N-1 ... 0`:
- `K_k = (R + B^T P_(k+1) B)^(-1) B^T P_(k+1) A`
- `P_k = Q + A^T P_(k+1) (A - B K_k)`

Then run a closed-loop rollout for `rollout_steps` starting from `x0`:
- `u_k = -K_k x_k`
- `x_(k+1) = A x_k + B u_k`

Write exactly these output files:
1. `/root/similar_lqr_rollout_trace.json`
2. `/root/similar_lqr_audit_report.json`

`/root/similar_lqr_rollout_trace.json` must be JSON with:
- `scenario`: string
- `records`: array with one entry per step
- each entry includes `k` (int), `x` (state vector), `u` (control vector), `stage_cost` (float)
- `terminal_state`: state vector after the last step
- `terminal_cost`: float

`/root/similar_lqr_audit_report.json` must be JSON with:
- `scenario`: string
- `state_dim`: int
- `control_dim`: int
- `horizon_N`: int
- `rollout_steps`: int
- `first_control`: control vector for step 0
- `gain_fro_norms`: array of Frobenius norms for all horizon gains
- `optimized_total_cost`: float
- `baseline_total_cost`: float (same rollout length with zero control)
- `cost_reduction_ratio`: float = `1 - optimized_total_cost / baseline_total_cost`
- `final_state`: state vector after rollout
- `terminal_value_from_P0`: float = `x0^T P_0 x0`
- `trace_file`: string, exactly `/root/similar_lqr_rollout_trace.json`
- `primary_output_file`: string, exactly `/root/similar_lqr_audit_report.json`

Rules:
1. Use only numbers from the case file.
2. Do not modify the case file.
3. Keep vector/matrix dimensions consistent with the case.
4. All numeric outputs must be computed from your own rollout results.
