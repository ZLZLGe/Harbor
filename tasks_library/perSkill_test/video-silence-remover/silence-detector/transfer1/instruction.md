Three per-second energy traces are available:

- `/root/clip_alpha_energies.json`
- `/root/clip_beta_energies.json`
- `/root/clip_gamma_energies.json`

Runtime parameters and clip metadata are in `/root/batch_config.json`.

Produce `/root/pre_roll_leaderboard.csv` with header:

```text
clip_id,silence_seconds,has_preroll,rank
```

Rules:

1. For each clip, detect the initial low-energy boundary using the exact parameters in `/root/batch_config.json`.
2. `silence_seconds` is the detected boundary second.
3. `has_preroll` is `yes` when `silence_seconds > 0`, otherwise `no`.
4. Sort rows by `silence_seconds` descending, then `clip_id` ascending.
5. `rank` starts at `1` in sorted order.
6. Keep numeric values as plain integers in CSV.
