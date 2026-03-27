Triage a small nanoGPT hyperparameter sweep and recommend the next run.

Input files:
- `/root/sweep_results.jsonl` (one JSON object per line)
- `/root/sweep_goal.json`

Write exactly one JSON file to:
- `/root/transfer3_scaling_plan.json`

Rules:
- Ignore runs with `"oom": true`.
- For each eligible run:
  - `final_loss = val_curve[-1]`
  - `speed_penalty = 50000 / throughput_tok_s`
  - `score = final_loss + 0.02 * speed_penalty`
- Select the run with minimum `score`.
- Parameter estimate:
  - `estimated_params = 12 * n_layer * (n_embd ** 2) + 50257 * n_embd`
- Extra steps to target:
  - target is `target_val_loss` from `sweep_goal.json`
  - if `final_loss <= target`: `expected_extra_steps_to_target = 0`
  - else if latest loss drop (`val_curve[-2] - val_curve[-1]`) is `<= 0`: use `-1`
  - else `ceil((final_loss - target) / latest_loss_drop)`

Output fields:
- `selected_run_id`
- `selected_score` (rounded 6 decimals)
- `estimated_params` (int)
- `expected_extra_steps_to_target` (int)
- `target_val_loss`
- `top2` (array of two best runs, each with `run_id` and `score`, score rounded 6)

Constraints:
- Do not read from `/tests`.
- Round float outputs to 6 decimals.
