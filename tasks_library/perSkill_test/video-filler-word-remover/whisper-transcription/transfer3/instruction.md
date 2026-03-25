A panel discussion transcript package is provided at:

- `/root/data/transfer3_panel_segments.json`

Create `/root/transfer3_clip_plan.json`.

Input shape:

- Object with `session` and `segments`.
- Each segment has `segment_id` and `words`.
- Each word has absolute `word`, `start`, `end` timestamps in seconds.

Detect this filler vocabulary:

- `um`, `uh`, `hum`, `hmm`, `mhm`, `like`, `yeah`, `so`, `basically`, `well`, `okay`
- `you know`, `i mean`, `kind of`, `i guess`

Clip timing rules:

- `lead_in_seconds = 0.05`
- `merge_gap_seconds = 0.1`
- Word durations (seconds):
  - `uh: 0.30`, `um: 0.40`, `hum: 0.60`, `hmm: 0.60`, `mhm: 0.55`
  - `like: 0.30`, `yeah: 0.35`, `so: 0.25`, `well: 0.35`, `okay: 0.40`
  - `basically: 0.55`, `you know: 0.55`, `i mean: 0.50`, `kind of: 0.50`, `i guess: 0.50`
- Default duration for unknown fillers: `0.40`

Construct raw clips from each detection:

- `start = max(0, timestamp - lead_in_seconds)`
- `end = timestamp + duration(word)`

Then merge overlapping clips or clips separated by `<= merge_gap_seconds`.

Output format:

```json
{
  "clip_parameters": {
    "lead_in_seconds": 0.05,
    "merge_gap_seconds": 0.1,
    "word_durations": {}
  },
  "clips": [
    {"start": 0.0, "end": 0.0, "duration": 0.0, "trigger": "..."}
  ],
  "total_clips": 0,
  "total_duration_seconds": 0.0
}
```

Rules:

1. In each merged clip, keep `trigger` as the earliest filler word/phrase that contributed to that merged interval.
2. Round `start`, `end`, `duration`, and `total_duration_seconds` to 2 decimals.
3. Keep clips sorted by `start` ascending.
