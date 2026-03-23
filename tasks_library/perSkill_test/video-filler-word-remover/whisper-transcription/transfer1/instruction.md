A retrospective meeting transcript export is provided at:

- `/root/data/transfer1_meeting_words.json`

Create `/root/transfer1_filler_summary.json`.

The input JSON has this shape:

- `session_id`: string
- `words`: array of items with `word`, `start`, `end`

Detect filler words and phrases with the same vocabulary:

- `um`, `uh`, `hum`, `hmm`, `mhm`, `like`, `yeah`, `so`, `basically`, `well`, `okay`
- `you know`, `i mean`, `kind of`, `i guess`

Output format:

```json
{
  "total_hits": 0,
  "by_word": [
    {"word": "...", "count": 0, "first_timestamp": 0.0, "last_timestamp": 0.0}
  ],
  "top_filler": {"word": "...", "count": 0}
}
```

Rules:

1. Detection is case-insensitive.
2. Use `start` as the event timestamp.
3. Round timestamps to 2 decimals.
4. `by_word` must be sorted by `count` descending, then `word` ascending.
5. `top_filler` must match the first element of `by_word`.
