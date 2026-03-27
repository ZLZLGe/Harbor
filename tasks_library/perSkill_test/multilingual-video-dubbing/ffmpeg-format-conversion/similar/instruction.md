You are given one source video file at `/root/input.mp4`.

Create these outputs:
1. `/root/similar_master.mkv`
2. `/root/similar_audio.aac`
3. `/root/similar_report.json`

Requirements:
1. `similar_master.mkv` must keep both the video stream and audio stream from `input.mp4` without re-encoding.
2. `similar_audio.aac` must be audio-only, AAC codec, 48000 Hz, mono.
3. `similar_report.json` must be valid JSON with these fields:
   - `source_video_codec`
   - `source_audio_codec`
   - `mkv_container`
   - `mkv_duration_sec`
   - `aac_codec`
   - `aac_sample_rate_hz`
   - `aac_channels`
4. `mkv_duration_sec` must be numeric and represent the duration of `similar_master.mkv` in seconds.
