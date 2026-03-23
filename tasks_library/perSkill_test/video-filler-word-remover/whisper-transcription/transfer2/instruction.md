Support-call transcript turns with word timestamps are provided at:

- `/root/data/transfer2_support_turns.json`

Create `/root/transfer2_window_report.json`.

Input shape:

- Array of turn objects.
- Each turn has `speaker`, `turn_start`, and `words`.
- Each item in `words` has absolute `word`, `start`, `end` times in seconds.

Detect the same filler vocabulary:

- `um`, `uh`, `hum`, `hmm`, `mhm`, `like`, `yeah`, `so`, `basically`, `well`, `okay`
- `you know`, `i mean`, `kind of`, `i guess`

Build fixed 30-second windows: `[0,30)`, `[30,60)`, ... up to the last detected filler timestamp.

Output format:

```json
{
  "window_size_seconds": 30,
  "windows": [
    {
      "window_start": 0,
      "window_end": 30,
      "filler_count": 0,
      "density_per_minute": 0.0,
      "dominant_filler": ""
    }
  ],
  "peak_window_start": 0,
  "peak_window_count": 0
}
```

Rules:

1. `filler_count` is the number of detected filler events in that window.
2. `density_per_minute = filler_count * 2`, rounded to 2 decimals.
3. `dominant_filler` is the most frequent filler in that window; tie-break lexicographically; empty string when count is zero.
4. `peak_window_start` is the `window_start` of the highest `filler_count`; tie-break smallest `window_start`.
