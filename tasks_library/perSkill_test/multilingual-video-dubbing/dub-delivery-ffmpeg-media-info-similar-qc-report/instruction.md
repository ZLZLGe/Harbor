A Spanish dubbing delivery package has already been rendered for you.

Available inputs:
- `/root/package_manifest.json`: delivery requirements, timing tolerances, and the scheduled placement start for each speech clip.
- `/root/delivery/final_mix.mp4`: the delivered localized video.
- `/root/delivery/segments/seg_001.wav`
- `/root/delivery/segments/seg_002.wav`
- `/root/delivery/segments/seg_003.wav`

Write `/root/dub_qc_report.json`.

Use only media/container metadata plus the placement schedule in `/root/package_manifest.json`. Do not transcribe speech and do not do waveform matching.

Your JSON must have this exact structure:

```json
{
  "package_id": "string",
  "video_file": "/root/delivery/final_mix.mp4",
  "source_language": "string",
  "target_language": "string",
  "video_duration_sec": 0.0,
  "expected_video_duration_sec": 0.0,
  "video_duration_delta_sec": 0.0,
  "allowed_video_duration_delta_sec": 0.0,
  "dubbed_audio": {
    "codec_name": "string",
    "sample_rate_hz": 0,
    "channels": 0,
    "language_tag": "string"
  },
  "delivery_checks": {
    "video_duration_ok": true,
    "sample_rate_ok": true,
    "channels_ok": true,
    "language_tag_ok": true,
    "all_segment_audio_specs_ok": true,
    "all_segments_within_tolerance": true,
    "package_passes": true
  },
  "segments": [
    {
      "segment_id": "string",
      "segment_file": "/root/delivery/segments/seg_001.wav",
      "expected_start_sec": 0.0,
      "placed_start_sec": 0.0,
      "expected_end_sec": 0.0,
      "placed_end_sec": 0.0,
      "duration_sec": 0.0,
      "start_drift_sec": 0.0,
      "end_drift_sec": 0.0,
      "audio_sample_rate_hz": 0,
      "audio_channels": 0,
      "sample_rate_ok": true,
      "channels_ok": true,
      "within_tolerance": true
    }
  ]
}
```

Rules:
- `video_file` and every `segment_file` must be absolute `/root/...` paths.
- Round every reported duration and drift field to 3 decimals.
- `placed_end_sec` must be computed as `placed_start_sec + measured segment duration`.
- `sample_rate_ok` and `channels_ok` at the segment level are checked against the required values in the manifest.
- `within_tolerance` is true only if the segment audio spec matches and both absolute drifts are within the manifest tolerances.
- `package_passes` is true only if every top-level check is true.
