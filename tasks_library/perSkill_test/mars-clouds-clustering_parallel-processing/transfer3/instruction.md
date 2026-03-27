# Transfer - Alert Calibration Matrix

You are given event history at `/root/data/events.csv`.

Evaluate every threshold combination from:
- `wind_threshold`: 18, 22, 26, 30
- `dust_threshold`: 35, 45, 55, 65
- `cooldown_min`: 10, 20, 30

For each combination, compute:
- `precision`
- `recall`
- `false_alarm`

Only keep combinations with `precision >= 0.45`.

From the kept rows, compute the Pareto frontier for:
- maximize `recall`
- minimize `false_alarm`

Write exactly one CSV file:
- `/outputs/transfer3_alert_matrix.csv`

CSV schema and order:
- `recall,false_alarm,precision,wind_threshold,dust_threshold,cooldown_min`

Formatting rules:
- round `recall`, `false_alarm`, and `precision` to 5 decimal places
- integer threshold columns remain integers
- sort rows by `recall` descending, then `false_alarm` ascending, then `precision` descending
