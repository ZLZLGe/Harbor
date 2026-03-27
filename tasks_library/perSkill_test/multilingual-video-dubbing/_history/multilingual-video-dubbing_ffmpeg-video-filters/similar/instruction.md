You are given one source clip at `/root/input.mp4`.

Produce exactly one output file:
- `/outputs/similar_preview.mp4`

Requirements:
1. The output video stream must be exactly `640x360`.
2. The visual style must apply all of the following in one processing pass:
   - resize to `640x360`
   - a mild brightness/contrast polish
   - a gentle global blur
3. Encode the output video as H.264 and keep pixel format compatible with common players (`yuv420p`).
4. The output audio must be AAC, `48000 Hz`, mono.
5. Keep total duration close to the source clip (no trimming or concatenation).

Success criteria:
- `/outputs/similar_preview.mp4` exists and satisfies the stream/format constraints above.
