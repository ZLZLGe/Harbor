## Task

In `/app/inspection/videos`, I provide short industrial inspection clips. Each clip focuses on one target gauge. Some gauges use a red pointer on a linear dial, and some show the reading directly on a cyan numeric panel.

Read every video file in that directory. For each video:

1. examine the clip frame by frame,
2. find the earliest frame where the target gauge reaches its highest reading,
3. write `/app/inspection/gauge_maxima.csv`.

The CSV file must be UTF-8 text with exactly these columns:

- `video_filename`
- `peak_frame_id`
- `max_reading`

Additional rules:

- `peak_frame_id` must use the format `F0000`, where the number is the zero-based frame index in decoding order.
- `max_reading` must be written as a plain decimal number with exactly one digit after the decimal point and no unit.
- If multiple frames share the same maximum reading, choose the earliest one.
- Sort rows by `video_filename` in ascending order.
- Do not add extra columns, blank lines, markdown, or commentary.
- Ignore panel decorations and status lights.
- Pointer gauges use a linear `0.0` to `100.0` scale across the visible arc.
