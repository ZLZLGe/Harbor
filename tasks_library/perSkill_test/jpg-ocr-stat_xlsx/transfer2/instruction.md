## Task Description

`/app/workspace/visits.json` contains clinic visit aggregates with fields:

- `date`
- `clinic`
- `patients`
- `avg_wait_min`

Create `/app/workspace/transfer2.xlsx` with exactly one sheet `daily_summary` and exactly these columns:

- `date`
- `total_patients`
- `weighted_wait_min`

Rules:

1. Group rows by `date`.
2. `total_patients` is the sum of `patients` per day.
3. `weighted_wait_min = sum(patients * avg_wait_min) / total_patients`, rounded to 1 decimal.
4. If `total_patients` is zero, leave `weighted_wait_min` blank.
5. Sort rows by date ascending. Header row required. No extra sheets/columns/rows.
