You are given router logits for three dispatch windows in a 4-token x 4-expert setup.

Input file:
- `/root/transfer1_router_case.json`

For each window:
1. Apply log-space Sinkhorn-Knopp to convert logits into a doubly stochastic dispatch matrix.
2. Compute row sums, column sums, expert load vector (column sums), and mean token entropy.
3. Compute balance standard deviation (`std(expert_load)`).

Write exactly one output file:
- `/root/transfer1_router_balance_report.json`

Required JSON structure:
- `scenario`
- `tau`
- `num_iters`
- `window_summaries`: array with one item per input window; each item contains:
  - `window_id`
  - `row_sums`
  - `col_sums`
  - `expert_load`
  - `entropy_mean`
  - `balance_std`
- `global_metrics`:
  - `max_row_error`
  - `max_col_error`
  - `load_std_mean`
  - `mean_entropy`
  - `best_window_by_balance`

Rules:
1. Use only the provided input.
2. Keep full precision; do not round intermediate values.
3. `best_window_by_balance` is the `window_id` with minimum `balance_std`.
