The review range for the bundled clip is defined in `/root/review_region.json`.

A noisy speech-activity pass for that range is in `/root/activity_pass1.csv`. Build silence windows for the edit queue and write `/root/review_silence_windows.csv`.

Rules:
- Read all rows from `/root/activity_pass1.csv`.
- Sort by `start`.
- Merge neighboring rows when the next `start` is at most `0.25` seconds after the current `end`.
- After merging, drop any merged speech window shorter than `0.30` seconds.
- Compute silence windows inside the inclusive review range from `review_start_sec` to `review_end_sec`.
- Keep only silence windows with duration at least `0.40` seconds.
- Round every numeric value to 3 decimals.

Write CSV with this header:

```text
silence_id,start_sec,end_sec,duration_sec,left_context,right_context
```

`left_context` and `right_context` must be the surrounding speech segment IDs, or `START` / `END` for the range boundaries.
