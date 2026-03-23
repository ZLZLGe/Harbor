A source status video is available at `/root/transfer3_source.mp4`.

Named extraction windows are listed in:

- `/root/data/transfer3_windows.json`

Create these outputs in `/root/`:

1. directory `transfer3_window_pack/` containing one MP4 per named window
2. `transfer3_window_index.json`

Rules:

1. For each window, extract from `start` to `end` into `transfer3_window_pack/<window_id>.mp4`.
2. Preserve the window order from the JSON file.
3. `transfer3_window_index.json` must contain:
   - `source_video`
   - `output_dir`
   - `windows`
   - `total_windows`
   - `total_duration_seconds`
4. Each item in `windows` must include:
   - `window_id`
   - `purpose`
   - `start`
   - `end`
   - `duration`
   - `output_file`
5. `total_duration_seconds` must equal the sum of all item `duration` values.
