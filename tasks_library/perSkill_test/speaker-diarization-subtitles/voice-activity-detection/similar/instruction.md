The bundled clip `/root/input.mp4` already has a first-pass speech-activity draft in `/root/raw_activity_draft.json`.

Clean that draft and write `/root/final_speech_segments.json`.

Rules:
- Read the `segments` array from `/root/raw_activity_draft.json`.
- Sort rows by `start`.
- Merge neighboring rows when the next `start` is at most `0.25` seconds after the current `end`.
- After merging, drop any merged window shorter than `0.30` seconds.
- Round every `start`, `end`, and `duration` value to 3 decimals.
- Preserve the input `clip_id`.

Write JSON in this shape:

```json
{
  "clip_id": "example",
  "segment_count": 0,
  "total_speech_sec": 0.0,
  "first_start_sec": 0.0,
  "last_end_sec": 0.0,
  "speech_segments": [
    {
      "segment_id": "speech_01",
      "start_sec": 0.0,
      "end_sec": 0.0,
      "duration_sec": 0.0,
      "source_ids": ["row_1"]
    }
  ]
}
```

Success criteria:
- The output file exists at `/root/final_speech_segments.json`.
- The speech windows reflect the cleanup rules exactly.
- `segment_id` values are sequential in chronological order starting from `speech_01`.
