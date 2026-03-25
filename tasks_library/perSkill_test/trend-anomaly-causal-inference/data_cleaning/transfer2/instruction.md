Clean the supplied field sensor reading table so it can be used in downstream reporting.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer2_sensor_readings_cleaned.csv`
- `/root/transfer2_sensor_readings_summary.json`

Cleaning rules:
- remove duplicate business records
- drop rows missing the critical identifier, date, or grouping fields
- normalize embedded text fields so they are useful for later analysis
- keep suspicious numeric spikes by capping them instead of discarding the entire record
