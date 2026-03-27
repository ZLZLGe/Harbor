You are given pre-extracted tracking records for multiple street-camera videos in `/root/video_tracks.json`.

Create an Excel file at `/root/similar_count.xlsx` with exactly one sheet named `results`.

The sheet must contain exactly two columns in this order:
1. `filename`
2. `number`

Rules:
1. For each video, count unique people where `label == "pedestrian"`.
2. A person can appear in multiple frames, but if `track_id` is the same in one video, count only once.
3. Ignore non-pedestrian labels.
4. Output rows sorted by `filename` ascending.
5. No extra sheets, columns, or rows.
