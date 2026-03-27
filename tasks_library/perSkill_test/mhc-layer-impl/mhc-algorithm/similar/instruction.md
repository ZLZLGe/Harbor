You are given a compact residual-stream case for an mHC-style block.

Input file:
- `/root/similar_case.json`

Run the following pipeline:
1. Compute `H_res` by applying log-space Sinkhorn-Knopp to `h_res_logits`.
2. Reshape residuals to `(batch, seq, streams, dim)` and perform residual stream mixing with `H_res`.
3. Compute branch input from `h_pre_logits`, apply the provided linear branch matrix, and redistribute branch output using `h_post_logits`.
4. Add redistributed branch output to mixed residuals.

Write exactly one output file:
- `/root/similar_mhc_stability_report.json`

The JSON must include these keys:
- `scenario`
- `sinkhorn`:
  - `row_sums` (length = number of streams)
  - `col_sums` (length = number of streams)
  - `max_row_error`
  - `max_col_error`
  - `min_entry`
  - `max_entry`
- `stream_means` (length = number of streams; mean over batch/seq/dim)
- `metrics`:
  - `input_energy`
  - `output_energy`
  - `energy_ratio`
  - `output_checksum`
  - `dominant_stream`
- `tensor_shape` (the final tensor shape as `[batch, seq, streams, dim]`)

Rules:
1. Use only data from the input file.
2. Use numerically stable log-space normalization.
3. Keep full precision in calculations; do not round intermediate values.
4. `dominant_stream` is the index of the largest absolute value in `stream_means`.
