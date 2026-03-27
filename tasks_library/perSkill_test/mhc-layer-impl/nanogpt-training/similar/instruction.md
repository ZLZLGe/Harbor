Prepare a stability summary for a tiny nanoGPT training experiment.

Input file:
- `/root/training_trace.json`

Write exactly one JSON file to:
- `/root/similar_report.json`

Required fields in `similar_report.json`:
- `scenario` (string; copy from input)
- `baseline_final_loss` (float; last baseline validation loss)
- `mhc_final_loss` (float; last mHC validation loss)
- `baseline_grad_norm_std` (float; population standard deviation)
- `mhc_grad_norm_std` (float; population standard deviation)
- `baseline_max_grad_norm` (float)
- `mhc_max_grad_norm` (float)
- `h_res_max_row_sum_error` (float; max absolute row-sum error from 1.0 across all `h_res_matrices`)
- `h_res_max_col_sum_error` (float; max absolute column-sum error from 1.0 across all `h_res_matrices`)
- `preferred_model` (string; `"mhc"` if `mhc_final_loss <= baseline_final_loss`, otherwise `"baseline"`)

Rules:
- Do not read from `/tests`.
- Compute metrics from input values; do not hardcode.
- Round all float outputs to 6 decimal places.
