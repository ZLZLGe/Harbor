You are triaging exported evidence clips before they are uploaded to a digital evidence system.

Available inputs:
- `/root/evidence_batch.json`: case metadata, intake rules, clip inventory, and device priority order.
- `/root/evidence/`: the listed bodycam and CCTV exports.

Write `/root/evidence_clip_audit.json`.

Use only media/container metadata from the listed files plus the rules in `/root/evidence_batch.json`. Do not inspect frame content manually and do not transcribe audio.

Your JSON must have this exact structure:

```json
{
  "case_id": "string",
  "incident_label": "string",
  "submission_target": "string",
  "recommended_submission_file": "/root/evidence/example.mp4",
  "technical_audit_summary": {
    "total_files": 0,
    "submission_ready_files": 0,
    "missing_audio_files": 0,
    "resolution_anomaly_files": 0,
    "duration_anomaly_files": 0,
    "codec_policy_violation_files": 0
  },
  "clips": [
    {
      "file": "/root/evidence/example.mp4",
      "device_role": "bodycam",
      "container_format": "string",
      "duration_sec": 0.0,
      "duration_delta_sec": 0.0,
      "width": 0,
      "height": 0,
      "video_codec": "string",
      "audio_track_count": 0,
      "audio_codec": null,
      "eligible_for_submission": true,
      "submission_rank": 1,
      "anomalies": []
    }
  ]
}
```

Rules:
- `recommended_submission_file` and every clip `file` must be absolute `/root/...` paths.
- Sort `clips` by `file`.
- Round `duration_sec` and `duration_delta_sec` to 3 decimals.
- `duration_delta_sec` must be `measured_duration_sec - expected_duration_sec`.
- `container_format` must come from the probed container metadata.
- `audio_codec` must be `null` when `audio_track_count` is `0`; otherwise it must be the first audio stream codec.
- `eligible_for_submission` is `true` only when `anomalies` is empty.
- `submission_rank` must be `0` for non-eligible clips. Eligible clips are ranked starting at `1` using this order: device role priority from the batch file, then smaller absolute `duration_delta_sec`, then `file`.
- `recommended_submission_file` must equal the file with `submission_rank` `1`.
- `anomalies` may contain only these exact strings, and if more than one applies they must stay in this order:
  - `missing_audio_track`
  - `unexpected_resolution`
  - `duration_out_of_range`
  - `disallowed_codec`
- `technical_audit_summary` counts how many files contain each anomaly and how many are submission-ready.
