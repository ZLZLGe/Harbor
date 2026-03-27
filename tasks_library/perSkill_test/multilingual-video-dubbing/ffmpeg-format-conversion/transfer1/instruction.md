You are given one source video file at `/root/input.mp4`.

Create these outputs:
1. `/root/transfer1_briefing.opus`
2. `/root/transfer1_manifest.json`

Requirements:
1. `transfer1_briefing.opus` must be audio-only, encoded as Opus, 48000 Hz, mono.
2. The output duration must stay within 0.25 seconds of the source media duration.
3. `transfer1_manifest.json` must be valid JSON with these fields:
   - `source_container`
   - `target_audio_codec`
   - `target_sample_rate_hz`
   - `target_channels`
   - `source_duration_sec`
   - `output_duration_sec`
