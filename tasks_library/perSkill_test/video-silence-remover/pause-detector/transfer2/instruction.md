Three one-second energy timelines are provided:

- `/root/data/transfer2_room_a.json`
- `/root/data/transfer2_room_b.json`
- `/root/data/transfer2_room_c.json`

Create `/root/transfer2_pause_break_index.csv`.

Detection parameters for each timeline:

- `start_time = 1`
- `threshold_ratio = 0.58`
- `min_duration = 2`
- `window_size = 5`

CSV requirements:

1. Header must be exactly:
   `session_id,detected_break_count,first_break_start,total_pause_seconds,longest_pause_seconds`
2. One row per session.
3. Sort rows by ascending `session_id`.
4. `first_break_start` is `-1` when no break is detected.
5. All count and duration fields must be integers.
