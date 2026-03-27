A camera gimbal small-angle linear model is provided in `/root/task_data.json`.

Produce `/root/transfer1_gimbal_sequence.csv` with columns:

`k,u_k,x1,x2,x3`

Rules:
1. Read `A`, `B`, `Q`, `R`, `N`, `x0`, `u_min`, and `u_max` from `/root/task_data.json`.
2. Use terminal matrix `P_N = Q`.
3. For `k = N-1 ... 0`, compute:
   - `K_k = (R + B^T P_{k+1} B)^(-1) B^T P_{k+1} A`
   - `P_k = Q + A^T P_{k+1} (A - B K_k)`
4. Roll forward from `x0` for exactly `N` rows:
   - `u_k_raw = -K_k x_k`
   - `u_k = clip(u_k_raw, u_min, u_max)`
   - write row `k,u_k,x1,x2,x3` using the current state `x_k`
   - update `x_{k+1} = A x_k + B u_k`
5. Keep floating-point precision; do not round to integers.
