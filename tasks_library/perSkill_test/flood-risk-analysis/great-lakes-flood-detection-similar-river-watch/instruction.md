Review the Wisconsin gauge roster in `/root/data/wisconsin_gauges.txt`.

For the spring high-water window from `2025-03-18` through `2025-03-22`, use the timestamped stage observations in `/root/data/wisconsin_stage_observations.csv` together with the flood stages in `/root/data/wisconsin_flood_thresholds.csv` to compute each listed station's daily maximum stage.

Write `/root/output/river_watch_summary.json` as a JSON array sorted by `flood_days` descending and then `station_id` ascending. Keep only stations that had at least one flood day during the window. Each array item must contain:

- `station_id`
- `flood_days`
- `flood_dates` as ascending `YYYY-MM-DD` strings for days where the daily maximum stage was greater than or equal to the station's flood stage
