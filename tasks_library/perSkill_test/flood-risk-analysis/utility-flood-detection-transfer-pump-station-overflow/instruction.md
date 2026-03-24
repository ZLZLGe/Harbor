Review `/root/data/pump_station_roster.txt`, `/root/data/pump_station_thresholds.tsv`, and `/root/data/wet_well_readings.jsonl`.

For the operations window from `2025-08-11` through `2025-08-15` inclusive, each JSON line is one 15-minute wet-well sensor reading with `pump_station_id`, `recorded_at`, and `wet_well_level_ft`.

For each rostered pump station that also has a threshold entry, compute the daily maximum wet-well level. A day counts as an overflow-risk day when that daily maximum is greater than or equal to the station's `overflow_level_ft`.

Write `/root/output/pump_station_overflow_report.csv` with only stations that had at least one overflow-risk day. Set `first_overflow_date` to the earliest overflow-risk day for that station in the reporting window.

Sort rows by `first_overflow_date` ascending, then `overflow_risk_days` descending, then `pump_station_id` ascending. The CSV must contain exactly these columns:

- `pump_station_id`
- `overflow_risk_days`
- `first_overflow_date`
