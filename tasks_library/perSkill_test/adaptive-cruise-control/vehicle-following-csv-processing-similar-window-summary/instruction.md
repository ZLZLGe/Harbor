Create `summarize_following_windows.py` that reads `drive_telemetry.csv` and writes `following_window_summary.csv`.

The input CSV has columns:
- `time_s`
- `ego_speed_mps`
- `lead_speed_mps`
- `gap_m`

Rows with missing `lead_speed_mps` or missing `gap_m` represent open road with no detected lead vehicle. Segment the rows into contiguous windows using these rules:
- `open_road`: `lead_speed_mps` or `gap_m` is missing
- `following`: lead data is present and `gap_m > 15.0`
- `critical_gap`: lead data is present and `gap_m <= 15.0`
- Start a new window whenever the window type changes from the previous row

Also derive `ttc_s` for each row, but only when lead data is present and `ego_speed_mps > lead_speed_mps`:
- `ttc_s = gap_m / (ego_speed_mps - lead_speed_mps)`
- If the relative speed is zero or negative, treat TTC as invalid and exclude it from TTC statistics

Write one summary row per contiguous window to `following_window_summary.csv` with this exact column order:
- `window_id`
- `window_type`
- `start_time_s`
- `end_time_s`
- `sample_count`
- `avg_ego_speed_mps`
- `min_gap_m`
- `valid_ttc_count`
- `avg_valid_ttc_s`
- `min_valid_ttc_s`

Output requirements:
- `window_id` starts at `0` and increments by `1` for each new window
- `sample_count` and `valid_ttc_count` must be integers
- Round all numeric summary values other than counts to 3 decimal places
- For windows with no lead-vehicle samples, leave `min_gap_m` empty
- For windows with `valid_ttc_count == 0`, leave `avg_valid_ttc_s` and `min_valid_ttc_s` empty
- Do not modify `drive_telemetry.csv`

After creating the script, run it so that `following_window_summary.csv` exists in `/root`.
