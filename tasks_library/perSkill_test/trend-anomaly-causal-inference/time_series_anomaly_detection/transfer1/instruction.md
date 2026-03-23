Review the daily hospital department admission counts and rank departments by how unusual their March 2020 activity was relative to the January-February baseline.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer1_department_anomaly_index.csv`
- `/root/transfer1_department_anomaly_summary.json`

Requirements:
- train on all dates before March 1, 2020
- score only the March 2020 window
- return exactly one row per department with `Category` and `Anomaly_Index`
- sort by `Anomaly_Index` descending
