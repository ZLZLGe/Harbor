There is a per-second energy timeline at `/root/lecture_energies.json` and run parameters at `/root/detection_config.json`.

Produce `/root/initial_silence_report.json` with this structure:

```json
{
  "method": "energy_threshold",
  "segments": [
    {"start": 0, "end": 15, "duration": 15}
  ],
  "total_segments": 1,
  "total_duration_seconds": 15,
  "parameters": {
    "threshold_multiplier": 1.6,
    "initial_window": 12,
    "smoothing_window": 1
  },
  "analysis": {
    "initial_avg": 0.05,
    "threshold": 0.08
  }
}
```

Requirements:

1. Use the exact parameter values from `/root/detection_config.json`.
2. `segments` must describe the initial low-energy interval only.
3. `total_segments` must equal `len(segments)`.
4. `total_duration_seconds` must equal the detected end second.
5. Keep numeric fields as JSON numbers (not strings).
