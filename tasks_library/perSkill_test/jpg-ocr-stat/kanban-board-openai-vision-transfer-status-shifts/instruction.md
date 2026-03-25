## Task

Two snapshots of the same kanban board are available here:

- `/app/workspace/board_snapshots/board_morning.png`
- `/app/workspace/board_snapshots/board_evening.png`

The board has exactly four columns from left to right:

- `Queued`
- `Building`
- `Review`
- `Shipped`

Read both images and create `/app/workspace/kanban_status_diff.ndjson`.

Output requirements:

- Write one JSON object per line.
- Each line must contain exactly these four keys: `card_text`, `from_column`, `to_column`, `change_type`.
- `card_text` must be the visible card title exactly as shown on the board.
- `from_column` is the morning column name. If a card only appears in the evening snapshot, use the empty string `""`.
- `to_column` is the evening column name. If a card only appears in the morning snapshot, use the empty string `""`.
- `change_type` must be one of:
  - `unchanged`
  - `moved`
  - `new_card`
  - `removed_card`
- Use `unchanged` only when the card appears in both snapshots and stays in the same column.
- Use `moved` only when the card appears in both snapshots and changes columns.
- Use `new_card` only when the card appears only in the evening snapshot.
- Use `removed_card` only when the card appears only in the morning snapshot.
- Include every unique card that appears in either snapshot exactly once.
- Sort the output lines by `card_text` in ascending order.
- Do not add extra keys, comments, blank lines, or extra output files.

The verifier checks NDJSON parseability, required fields, uniqueness, movement semantics, ordering, and exact record content.
