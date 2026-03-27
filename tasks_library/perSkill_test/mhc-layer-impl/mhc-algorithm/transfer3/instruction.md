You are given 6-step forecasts from 4 models and one observed target trajectory.

Input file:
- `/root/transfer3_forecast_case.json`

Pipeline:
1. Build a doubly stochastic blend matrix from `blend_logits` using log-space Sinkhorn-Knopp.
2. Mix the forecast streams with the blend matrix.
3. Compare baseline (unmixed) and mixed ensembles.

Write exactly one output file:
- `/root/transfer3_forecast_stability_report.json`

Required JSON structure:
- `scenario`
- `tau`
- `num_iters`
- `baseline_ensemble` (length horizon)
- `mixed_ensemble` (length horizon)
- `sinkhorn`:
  - `row_sums`
  - `col_sums`
  - `max_row_error`
  - `max_col_error`
- `metrics`:
  - `baseline_stream_variance`
  - `mixed_stream_variance`
  - `variance_reduction`
  - `baseline_rmse`
  - `mixed_rmse`
  - `rmse_improvement`
  - `mixed_checksum`

Rules:
1. Use only the provided input.
2. Keep full precision; do not round intermediate values.
3. `variance_reduction` is `baseline_stream_variance - mixed_stream_variance`.
4. `rmse_improvement` is `baseline_rmse - mixed_rmse`.
