Build a deterministic token-loader audit report for a GPT-style next-token setup.

Input file:
- `/root/token_shards.json`

Write exactly one JSON file to:
- `/root/transfer1_loader_report.json`

Definitions:
- Concatenate all shard arrays in order into one token stream `tokens`.
- For each `offset` in `offsets` and for each sample index `i` in `[0, batch_size)`:
  - `start = (offset + i * block_size) % len(tokens)`
  - Build a circular window of length `block_size + 1` from `tokens` starting at `start`.
  - `x = window[:-1]`, `y = window[1:]`.
- `coverage_ratio` is `(number of unique token ids appearing in any x sequence) / (number of unique token ids in tokens)`.

Required output structure:
- `scenario` (string)
- `num_sequences` (int)
- `unique_token_count` (int)
- `coverage_ratio` (float, rounded to 6 decimals)
- `batches` (array)
  - each element has `offset`, `x`, `y`

Rules:
- Do not read from `/tests`.
- Preserve integer token ids.
- Round only `coverage_ratio` to 6 decimals.
