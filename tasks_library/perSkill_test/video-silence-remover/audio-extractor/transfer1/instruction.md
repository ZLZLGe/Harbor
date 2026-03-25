A compliance reviewer needs a short preview extracted from the provided video.

Input:
- `/root/data/input_video.mp4`

Save:
- `/root/preview_audio.wav`
- `/root/preview_audio_manifest.json`

Requirements:
- export only the first 45 seconds of audio
- convert it into a mono WAV file sampled at 8000 Hz
- record `sample_rate`, `channels`, `sample_width_bytes`, `frame_count`, and `duration_seconds` in the manifest
- ensure the manifest values match the produced WAV file
