You are given one source clip at `/root/input.mp4`.

Produce one output file:
- `/outputs/transfer3_watermark_master.mp4`

Requirements:
1. Render a mastered delivery copy at exactly `960x540`.
2. The visual pipeline must include all of the following:
   - resize to `960x540`
   - a persistent bottom-right corner mark made from two translucent rectangular layers
   - a subtle overall softening pass
3. Encode video as H.264 and pixel format `yuv420p`.
4. Encode audio as AAC, `48000 Hz`, mono.
5. Keep timeline continuity (no manual cuts).

Success criteria:
- `/outputs/transfer3_watermark_master.mp4` exists and matches the above constraints.
