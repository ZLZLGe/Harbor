Review `/root/data/reservoir_roster.txt`, `/root/data/spillway_thresholds.csv`, and `/root/data/reservoir_hourly_levels.json`.

For the operations window from `2025-10-03` through `2025-10-07` inclusive, each JSON record provides 24 hourly pool elevations for one reservoir and one day. For each reservoir in the roster, compute that day's peak pool elevation as the maximum value in `hourly_levels_ft`.

A reservoir belongs in the output only if it had at least one day whose peak pool elevation was greater than or equal to its `flood_stage_ft`. Reservoirs that only reached action stage should be omitted.

Set `highest_severity` from the worst daily peak during the window:

- `major` if any daily peak is greater than or equal to `major_stage_ft`
- otherwise `flood`

Set `peak_day` to the `YYYY-MM-DD` date of the highest daily peak during the window. If two days tie for the same peak elevation, use the earlier date.

Write `/root/output/spillway_alerts.json` as a JSON object with these top-level keys:

- `report_window`, containing `start_date` and `end_date`
- `summary`, containing `reservoirs_evaluated` and `reservoirs_with_flood_stage`
- `reservoir_alerts`, sorted by `flood_risk_days` descending, then `peak_level_ft` descending, then `reservoir_id` ascending

Each item in `reservoir_alerts` must contain exactly these fields:

- `reservoir_id`
- `reservoir_name`
- `flood_risk_days`
- `highest_severity`
- `peak_day`
- `peak_level_ft`
