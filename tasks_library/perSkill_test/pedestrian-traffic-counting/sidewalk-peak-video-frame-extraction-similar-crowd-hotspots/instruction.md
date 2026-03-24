## Task

In `/app/video`, I provide several fixed-camera sidewalk surveillance clips.

For each video file in that directory:

1. Turn the clip into a comparable sequence of still frames.
2. Find the frame that shows the largest number of pedestrians visible at the same time.
3. Record the result in `/app/video/pedestrian_peaks.xlsx`.

The workbook must contain exactly one sheet named `results` with exactly these columns:

- `filename`: the source video filename.
- `peak_frame_id`: the winning frame identifier in the format `F0000`, using a zero-based frame index padded to 4 digits.
- `visible_pedestrians`: the number of pedestrians visible in that frame.

Additional rules:

- If multiple frames tie for the largest visible pedestrian count, choose the earliest frame.
- Count pedestrians that are at least partially visible inside the frame.
- Ignore static street objects and road markings.
- The first row must be the header row.
- Sort output rows by `filename` in ascending order.
- Do not add extra sheets, columns, or rows.
