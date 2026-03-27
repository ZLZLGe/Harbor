You are given a small multi-sensor stream case with three streams and five timesteps.

Input file:
- `/root/transfer2_sensor_case.json`

Pipeline:
1. Compute doubly stochastic `H_res` from logits using log-space Sinkhorn-Knopp.
2. Mix residual streams with `H_res`.
3. Build branch input from `h_pre_logits`, apply the provided branch matrix, and redistribute with `h_post_logits`.
4. Add redistributed branch output to mixed residual streams.
5. Produce a fused series by averaging the final tensor across stream dimension.

Write exactly one output file:
- `/root/transfer2_sensor_fusion_report.json`

Required JSON structure:
- `scenario`
- `tau`
- `num_iters`
- `fused_series` (array of length timesteps, each entry length feature_dim)
- `consistency_curve` (length timesteps; per-step mean std across streams)
- `sinkhorn`:
  - `row_sums`
  - `col_sums`
  - `max_row_error`
  - `max_col_error`
- `metrics`:
  - `mean_consistency`
  - `max_consistency`
  - `reference_drift_l2`
  - `output_checksum`

Rules:
1. Use only the provided input.
2. Keep full precision in intermediate values.
3. `reference_drift_l2` is the L2 norm between `fused_series` and `reference_fused`.
