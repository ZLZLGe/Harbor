Analyze the daily category spending ledger and rank product categories by how unusual their March 2020 behavior was compared with the January-February baseline.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/similar_category_anomaly_index.csv`
- `/root/similar_category_anomaly_summary.json`

Requirements:
- use all data before March 1, 2020 as the training baseline
- evaluate anomalies during March 2020 only
- return one row per category with columns `Category` and `Anomaly_Index`
- sort the final file by `Anomaly_Index` descending
- positive scores should reflect unusual surges, negative scores unusual slumps
