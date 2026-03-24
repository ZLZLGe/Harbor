Review `/root/data/underpass_thresholds.json` and `/root/data/underpass_depth_readings.csv`.

For the reporting window from `2025-09-10` through `2025-09-14` inclusive, treat the 5-minute `depth_cm` readings as instantaneous water depth at each underpass and compute each underpass's daily maximum depth.

A day counts as a blocked day when that daily maximum is greater than or equal to the underpass's `traffic_control_depth_cm`.

Set `worst_closure_category` to:

- `full_closure` if any daily maximum during the reporting window is greater than or equal to `full_closure_depth_cm`
- otherwise `traffic_control`

Write `/root/output/underpass_closure_days.csv` with only the underpasses that had at least one blocked day. Sort the rows by `blocked_days` descending and then `underpass_id` ascending. The CSV must contain exactly these columns:

- `underpass_id`
- `blocked_days`
- `worst_closure_category`
