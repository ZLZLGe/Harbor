You are doing a technical ingest review for a TV station.

Inputs:
- `/root/ingest_requirements.json`: campaign metadata, candidate file list, and the ingest spec.
- `/root/candidates/`: the candidate ad masters listed in the requirements file.

Write `/root/ad_ingest_report.json`.

Use only media/container metadata from the candidate files plus the ingest spec. Do not inspect the visual content frame-by-frame and do not transcribe audio.

Your JSON must have this exact structure:

```json
{
  "campaign_id": "string",
  "station_id": "string",
  "spec_version": "string",
  "decision": "accept_single_version",
  "accepted_file": "/root/candidates/example.mp4",
  "accepted_summary": {
    "duration_sec": 0.0,
    "video_codec": "string",
    "width": 0,
    "height": 0,
    "frame_rate_fps": 0.0,
    "audio_codec": "string",
    "audio_channel_layout": "string"
  },
  "reviewed_candidate_count": 0,
  "rejected_file_count": 0,
  "rejected_files": [
    {
      "file": "/root/candidates/example_bad.mp4",
      "reasons": [
        "duration_sec expected 15.000 got 15.080"
      ]
    }
  ]
}
```

Rules:
- `accepted_file` and every rejected `file` must be absolute `/root/...` paths.
- Round `duration_sec` and `frame_rate_fps` to 3 decimals.
- `decision` must be `accept_single_version`.
- `reviewed_candidate_count` must equal the number of listed candidates.
- `rejected_file_count` must equal the length of `rejected_files`.
- Include every non-accepted candidate exactly once in `rejected_files`, sorted by `file`.
- Each `reasons` list must preserve this check order whenever a candidate fails: duration, resolution, frame rate, video codec, audio codec, audio channel layout.
- Use these exact message templates when a check fails:
  - `duration_sec expected <expected> got <actual>`
  - `resolution expected <expected_width>x<expected_height> got <actual_width>x<actual_height>`
  - `frame_rate_fps expected <expected> got <actual>`
  - `video_codec expected <expected> got <actual>`
  - `audio_codec expected <expected> got <actual>`
  - `audio_channel_layout expected <expected> got <actual>`
