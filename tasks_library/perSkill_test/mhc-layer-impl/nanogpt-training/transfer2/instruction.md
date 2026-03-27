Evaluate optimizer traces from a compact GPT training study.

Input file:
- `/root/optimizer_runs.json`

Write exactly one JSON file to:
- `/root/transfer2_optimizer_report.json`

Definitions:
- Learning rate schedule uses warmup + cosine decay:
  - if `step < warmup_steps`: `lr = max_lr * (step + 1) / warmup_steps`
  - else if `step >= max_steps`: `lr = min_lr`
  - else `lr = min_lr + 0.5 * (1 + cos(pi * decay_ratio)) * (max_lr - min_lr)`
    where `decay_ratio = (step - warmup_steps) / (max_steps - warmup_steps)`
- Standard deviation is population standard deviation.
- `best_optimizer` is the one with lower final validation loss; tie-break with lower grad std.

Required fields:
- `scenario`
- `adamw_final_loss`
- `muon_final_loss`
- `adamw_grad_norm_std`
- `muon_grad_norm_std`
- `adamw_max_grad_norm`
- `muon_max_grad_norm`
- `best_optimizer`
- `lr_checkpoints` (object with string step keys)

Rules:
- Do not read from `/tests`.
- Round float outputs to 6 decimals.
