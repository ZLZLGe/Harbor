You are given one source clip at `/root/input.mp4`.

Produce one output file:
- `/outputs/transfer2_fastcut.mp4`

Requirements:
1. Render a shorter, faster playback variant for promo usage.
2. Final video resolution must be `854x480`.
3. The visual pipeline must include both:
   - resizing to final resolution
   - a mild detail-enhancement pass
4. Increase playback speed uniformly for both video and audio.
5. Encode video as H.264 (`yuv420p`).
6. Encode audio as AAC, `48000 Hz`, mono.

Success criteria:
- `/outputs/transfer2_fastcut.mp4` exists and matches the stream and timing behavior above.
