You are reviewing one refrigerated trailer trip after delivery.

Input files available in `/root`:
- `temperature_log.csv`
- `door_events.csv`

Create `analyze_excursions.py` and run it. The script must read both CSV files and produce:
- `excursion_windows.csv`
- `excursion_summary.json`

Do not modify the input files.

`temperature_log.csv` columns:
- `recorded_at`
- `compartment`
- `temperature_c`
- `upper_limit_c`

`door_events.csv` columns:
- `event_time`
- `event_type`

Use these fixed analysis rules:
- Sort temperature rows by `compartment`, then `recorded_at`
- The sampling interval is always 10 minutes
- Blank `temperature_c` cells represent missing samples; forward-fill them within the same compartment before classifying excursions
- A sample is in excursion when the filled temperature is strictly greater than `upper_limit_c`
- Build excursion windows separately for each compartment
- A window is a maximal consecutive run of excursion samples within one compartment
- Treat each excursion sample as covering the 10-minute interval that starts at its `recorded_at`
- `start_time` is the timestamp of the first excursion sample in the window
- `end_time` is 10 minutes after the timestamp of the last excursion sample in the window
- `duration_minutes` is the whole-minute difference between `end_time` and `start_time`
- `imputed_sample_count` counts excursion rows whose original `temperature_c` was blank before forward-fill
- `max_temperature_c` is the highest filled temperature inside the window
- `max_excursion_c = max_temperature_c - upper_limit_c`
- `peak_recorded_at` is the earliest timestamp in the window where `max_temperature_c` occurs
- Build door-open intervals from each `open` event until the next `close` event
- `door_open_minutes` is the total minute overlap between the window interval and all door-open intervals
- `door_open_cycle_count` counts how many door-open intervals overlap the window
- `door_open_during_window` must be lowercase `true` when `door_open_minutes > 0`, otherwise lowercase `false`

Write `excursion_windows.csv` with exactly these columns in this exact order:
1. `window_id`
2. `compartment`
3. `start_time`
4. `end_time`
5. `sample_count`
6. `imputed_sample_count`
7. `duration_minutes`
8. `limit_c`
9. `max_temperature_c`
10. `max_excursion_c`
11. `peak_recorded_at`
12. `door_open_minutes`
13. `door_open_during_window`
14. `door_open_cycle_count`

Output requirements:
- Sort rows by `compartment`, then `start_time`
- Assign `window_id` after that final sort using `EXC-001`, `EXC-002`, and so on
- Round `limit_c`, `max_temperature_c`, and `max_excursion_c` to 3 decimals
- Keep integer count and duration columns as integers

Write `excursion_summary.json` with exactly these top-level keys:
- `window_count`
- `affected_compartments`
- `windows_with_door_open`
- `longest_window_minutes`
- `worst_excursion_c`
- `total_door_open_minutes_during_excursions`

Summary requirements:
- `affected_compartments` must be sorted ascending
- Round numeric summary values to 3 decimals when needed
