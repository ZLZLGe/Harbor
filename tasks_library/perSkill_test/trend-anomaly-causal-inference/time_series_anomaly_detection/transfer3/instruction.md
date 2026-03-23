Analyze the daily genre-level watch-hour totals and rank genres by how unusual their March 2020 patterns were versus the January-February baseline.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer3_genre_anomaly_index.csv`
- `/root/transfer3_genre_anomaly_summary.json`

Requirements:
- model the baseline with all history before March 1, 2020
- evaluate only March 2020 for anomaly scoring
- return one row per genre with columns `Category` and `Anomaly_Index`
- sort descending by `Anomaly_Index`
