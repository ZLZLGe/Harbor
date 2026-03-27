A battery-pack balancing linear model is provided in `/root/task_data.json`.

Create `/root/transfer3_balance_actions.json` with this shape:

```json
{
  "scenario": "battery_balance_pack",
  "horizon": 7,
  "first_three_controls": [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
  "terminal_state": [0.0, 0.0, 0.0, 0.0, 0.0],
  "quadratic_score": 0.0
}
```

Rules:
1. Read `A`, `B`, `Q`, `R`, `N`, and `x0` from `/root/task_data.json`.
2. Use `P_N = Q` and the same backward Riccati recursion:
   - `K_k = (R + B^T P_{k+1} B)^(-1) B^T P_{k+1} A`
   - `P_k = Q + A^T P_{k+1} (A - B K_k)`
3. Forward rollout for `k = 0..N-1`:
   - `u_k = -K_k x_k`
   - `x_{k+1} = A x_k + B u_k`
4. `first_three_controls` stores `u_0`, `u_1`, `u_2`.
5. `terminal_state` is `x_N`.
6. `quadratic_score` is:
   - `sum_{k=0}^{N-1} (x_k^T Q x_k + u_k^T R u_k) + x_N^T Q x_N`.
