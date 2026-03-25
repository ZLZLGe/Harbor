Build an audio excerpt that can be attached to a case review packet.

Input:
- `/root/data/input_video.mp4`

Save:
- `/root/evidence_excerpt.wav`
- `/root/evidence_excerpt_manifest.json`

Requirements:
- export only the first 120 seconds of audio
- convert it into a mono WAV file sampled at 16000 Hz
- record `sample_rate`, `channels`, `sample_width_bytes`, `frame_count`, and `duration_seconds` in the manifest
- ensure the manifest values match the produced WAV file
