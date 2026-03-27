You are given a source clip at `/root/input.mp4`.

Produce one output file:
- `/outputs/transfer1_vertical.mp4`

Requirements:
1. Reframe the clip into a vertical format intended for story playback.
2. Output video resolution must be exactly `720x1280`.
3. The processing must include all of the following:
   - center crop for portrait framing
   - resize to final resolution
   - a moderate color-intensity boost
4. Encode video as H.264 with `yuv420p` pixel format.
5. Encode audio as AAC, `48000 Hz`, mono.
6. Keep playback continuity (do not cut away sections of the timeline).

Success criteria:
- `/outputs/transfer1_vertical.mp4` exists and matches the above stream constraints.
