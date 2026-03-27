A roll-line section model has already been linearized and saved in `/root/task_data.json`.

Use the provided matrices to compute a finite-horizon quadratic-control first move with backward Riccati recursion.

Write `/root/similar_report.json` with this structure:

```json
{
  "scenario": "roll_line_step_recovery",
  "horizon": 8,
  "u0": [0.0, 0.0],
  "predicted_state_after_u0": [0.0, 0.0, 0.0, 0.0],
  "state_cost": 0.0
}
```

Rules:
1. Read `A`, `B`, `Q`, `R`, `N`, and `x0` from `/root/task_data.json`.
2. Use terminal matrix `P_N = Q`.
3. For `k = N-1 ... 0`, compute:
   - `K_k = (R + B^T P_{k+1} B)^(-1) B^T P_{k+1} A`
   - `P_k = Q + A^T P_{k+1} (A - B K_k)`
4. Compute `u0 = -K_0 x0`.
5. Compute `predicted_state_after_u0 = A x0 + B u0`.
6. Compute `state_cost = x0^T P_0 x0`.
7. Preserve numeric precision (do not round aggressively).
