Produce a short monitoring sample from the provided video for a QA desk.

Input:
- `/root/data/input_video.mp4`

Save:
- `/root/qa_monitor.wav`
- `/root/qa_monitor_manifest.json`

Requirements:
- export only the first 30 seconds of audio
- convert it into a mono WAV file sampled at 22050 Hz
- record `sample_rate`, `channels`, `sample_width_bytes`, `frame_count`, and `duration_seconds` in the manifest
- ensure the manifest values match the produced WAV file
