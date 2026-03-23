Create `/root/transfer2_quiet_intervals.json` from:

- `/root/data/night_watch.wav`

Output format:

```json
{
  "recording_id": "night-watch-3",
  "window_seconds": 1,
  "quiet_threshold": 15,
  "energies": [12, 10, 9, 80, 85, 8, 7],
  "quiet_intervals": [
    {"start": 0, "end": 3, "duration": 3},
    {"start": 5, "end": 7, "duration": 2}
  ],
  "total_quiet_seconds": 5
}
```

Rules:

1. Use 1-second windows.
2. A second is quiet when energy is `<= quiet_threshold`.
3. Merge consecutive quiet seconds into intervals `[start, end)`.
4. `duration` must equal `end - start`.
