Use the daily route-delay ledger to find which shipping routes showed unusual March 2020 behavior relative to the January-February trend.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer2_route_anomaly_index.csv`
- `/root/transfer2_route_anomaly_summary.json`

Requirements:
- use all observations before March 1, 2020 as the baseline window
- score anomalies during March 2020
- output one row per route with `Category` and `Anomaly_Index`
- sort the final ranking from highest anomaly to lowest
