Review `/root/data/wisconsin_station_roster.txt`, `/root/data/wisconsin_stage_observations.csv`, and `/root/data/wisconsin_threshold_report.csv`.

The threshold report follows a bulk gauge export format: data rows include one trailing field beyond the header row. Use the `flood stage` value as each station's flood threshold, ignore stations with missing or `-9999` thresholds, and determine which rostered Wisconsin stations reached flood stage at least once from `2025-06-10` through `2025-06-16`.

Write `/root/output/wisconsin_flood_window.csv` with exactly four columns in this order: `station_id`, `first_flood_date`, `flood_days`, `peak_stage_ft`.

Include only stations with at least one flood day. `first_flood_date` should be the first date in the window when the observed stage was greater than or equal to the station's flood stage. `peak_stage_ft` should be the maximum observed stage during the window for that station. Sort the rows by `first_flood_date` and then `station_id`.
