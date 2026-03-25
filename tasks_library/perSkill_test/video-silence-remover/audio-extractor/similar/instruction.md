Prepare an analysis-ready audio package for the teaching video.

Input:
- `/root/data/input_video.mp4`

Save:
- `/root/lecture_audio.wav`
- `/root/lecture_audio_manifest.json`

Requirements:
- convert the video soundtrack into a mono WAV file sampled at 16000 Hz
- keep the full usable duration of the source video
- record `sample_rate`, `channels`, `sample_width_bytes`, `frame_count`, and `duration_seconds` in the manifest
- ensure the manifest values match the produced WAV file
