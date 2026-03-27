You are given one source video file at `/root/input.mp4`.

Create these outputs:
1. `/root/transfer2_preview.webm`
2. `/root/transfer2_qc.json`

Requirements:
1. `transfer2_preview.webm` must contain both video and audio streams.
2. The video codec must be VP9.
3. The audio codec must be Opus.
4. The output duration must stay within 0.30 seconds of the source duration.
5. `transfer2_qc.json` must be valid JSON with these fields:
   - `container`
   - `video_codec`
   - `audio_codec`
   - `duration_sec`
   - `file_size_bytes`
