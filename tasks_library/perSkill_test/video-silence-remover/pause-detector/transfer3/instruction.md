Two energy timelines are provided:

- `/root/data/transfer3_narration_track.json`
- `/root/data/transfer3_screen_track.json`

Create `/root/transfer3_overlap_windows.json`.

Detection parameters:

- Narration track:
  - `start_time = 0`
  - `threshold_ratio = 0.56`
  - `min_duration = 2`
  - `window_size = 5`
- Screen track:
  - `start_time = 0`
  - `threshold_ratio = 0.60`
  - `min_duration = 2`
  - `window_size = 5`

Output requirements:

1. Include these top-level fields:
   - `narration_segments`
   - `screen_segments`
   - `overlap_segments`
   - `overlap_duration_seconds`
   - `joint_pause_count`
2. `overlap_segments` are intersections between narration and screen pause segments.
3. Each overlap segment must include `start`, `end`, and `duration`.
4. `overlap_duration_seconds` is the sum of overlap `duration` values.
5. `joint_pause_count` is the number of overlap segments.
