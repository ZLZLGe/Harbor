An annotated energy timeline is provided at:

- `/root/data/transfer1_board_session_energies.json`

Create `/root/transfer1_editorial_pause_audit.json` with this exact top-level structure:

```json
{
  "session_id": "...",
  "parameters": {
    "start_time": 0,
    "threshold_ratio": 0.0,
    "min_duration": 0,
    "window_size": 0
  },
  "pause_segments": [],
  "total_pause_seconds": 0,
  "longest_pause_seconds": 0,
  "top_two_segments": [],
  "qa_flag": "ok"
}
```

Rules:

1. Detect pauses from second `2` onward using:
   - `threshold_ratio = 0.6`
   - `min_duration = 2`
   - `window_size = 7`
2. Copy all detected segments into `pause_segments`.
3. `total_pause_seconds` is the sum of `duration` over all detected segments.
4. `longest_pause_seconds` is the max segment duration (0 if no segment).
5. `top_two_segments` contains at most two segments sorted by descending `duration`, tie-broken by smaller `start`.
6. Set `qa_flag` to:
   - `"needs-review"` if `longest_pause_seconds >= 4`
   - otherwise `"ok"`.
