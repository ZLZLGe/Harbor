A two-zone thermal model is stored in `/root/task_data.json`.

Create `/root/transfer2_hvac_dispatch.json` with this structure:

```json
{
  "scenario": "two_zone_hvac",
  "horizon": 6,
  "initial_temperature": [0.0, 0.0],
  "steps": [
    {
      "k": 0,
      "control": [0.0, 0.0],
      "predicted_temp": [0.0, 0.0]
    }
  ],
  "cumulative_control_l1": 0.0
}
```

Rules:
1. Read `A`, `B`, `Q`, `R`, `N`, `x0_abs`, and `x_ref` from `/root/task_data.json`.
2. Work in deviation coordinates: `dx = x_abs - x_ref`.
3. Use terminal matrix `P_N = Q` and backward Riccati recursion:
   - `K_k = (R + B^T P_{k+1} B)^(-1) B^T P_{k+1} A`
   - `P_k = Q + A^T P_{k+1} (A - B K_k)`
4. For each step `k = 0..N-1`:
   - `u_k = -K_k dx_k`
   - `dx_{k+1} = A dx_k + B u_k`
   - `x_abs_{k+1} = x_ref + dx_{k+1}`
5. In `steps`, store `k`, `control` (`u_k`), and `predicted_temp` (`x_abs_{k+1}`).
6. `cumulative_control_l1` must be the sum over all steps of `|u_1| + |u_2|`.
