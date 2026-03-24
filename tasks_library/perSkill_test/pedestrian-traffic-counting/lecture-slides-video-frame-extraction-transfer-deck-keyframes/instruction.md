## Task

In `/app/lectures/recordings`, I provide lecture screen recordings.

For every video file in that directory:

1. Extract candidate still frames in timeline order.
2. Deduplicate repeated views of the same slide.
3. Keep the earliest clear representative frame for each distinct slide.
4. Save the kept frames under `/app/lectures/keyframes/<video_stem>/` using the exact filename pattern `slide_%03d.jpg`.
5. Write `/app/lectures/slide_keyframes.json`.

`/app/lectures/slide_keyframes.json` must be a UTF-8 JSON array. Each element must be an object with exactly these fields:

- `video_filename`: the source video filename.
- `sequence_number`: a 1-based integer showing the kept slide order inside that video.
- `frame_filename`: the relative path from `/app/lectures` to the saved image, for example `keyframes/lecture-recording/slide_001.jpg`.

Additional rules:

- Sort the JSON array first by `video_filename` ascending, then by `sequence_number` ascending.
- Keep only one representative frame for each slide, even if that slide remains on screen for many frames.
- Ignore transitional duplicates after a slide has already been recorded.
- Do not include extra keys or markdown.
- Do not write anything outside `/app/lectures/keyframes/` and `/app/lectures/slide_keyframes.json`.
