The bundled clip `/root/input.mp4` has a line-delimited first-pass activity draft in `/root/burst_activity.jsonl`.

Clean the draft and write `/root/activity_burst_audit.json`.

Rules:
- Read every JSON line from `/root/burst_activity.jsonl`.
- Sort by `start`.
- Merge neighboring rows when the next `start` is at most `0.25` seconds after the current `end`.
- After merging, drop any merged speech window shorter than `0.30` seconds.
- Round every numeric value to 3 decimals.
- Treat a quiet gap as "long" when it is at least `quiet_gap_threshold_sec` from `/root/audit_config.json`.
- Treat a kept speech window as a micro burst when its duration is strictly less than `micro_burst_threshold_sec` from `/root/audit_config.json`.
- For `phase_totals_sec`, group kept speech by segment start time:
  - `phase_1_under_30` for starts below 30 seconds
  - `phase_2_30_to_60` for starts from 30 seconds up to but not including 60 seconds
  - `phase_3_60_plus` for starts at or above 60 seconds

Write JSON in this shape:

```json
{
  "kept_segment_count": 0,
  "total_speech_sec": 0.0,
  "first_speech_sec": 0.0,
  "last_speech_sec": 0.0,
  "longest_quiet_gap_sec": 0.0,
  "segments_after_quiet_gap": [
    {"segment_id": "speech_02", "gap_sec": 0.0}
  ],
  "micro_bursts": ["speech_09"],
  "phase_totals_sec": {
    "phase_1_under_30": 0.0,
    "phase_2_30_to_60": 0.0,
    "phase_3_60_plus": 0.0
  }
}
```
