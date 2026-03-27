You are given one source video file at `/root/input.mp4`.

Create these outputs:
1. `/root/transfer3_legacy.avi`
2. `/root/transfer3_index.csv`

Requirements:
1. `transfer3_legacy.avi` must include one video stream and one audio stream.
2. Video codec must be MPEG-4 (`mpeg4`).
3. Audio codec must be MP3, 44100 Hz, 2 channels.
4. `transfer3_index.csv` must be UTF-8 text with exactly two lines:
   - Header line: `file,container,video_codec,audio_codec,audio_sample_rate_hz,audio_channels`
   - Data line with values describing `transfer3_legacy.avi`.
