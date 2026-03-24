My data is in `/root/data/rail_reliability_yearly.csv`. Each row is one annual summary for the same rail network, but the rows are not sorted by year.

The columns are:

- `service_year`
- `late_departure_rate_pct`
- `missed_connection_rate_pct`
- `scheduled_train_km_millions`
- `weather_delay_days`

Please compare the two reliability KPIs `late_departure_rate_pct` and `missed_connection_rate_pct` to determine which one is worsening faster over time. Higher values are worse for both metrics.

Use this workflow:
- Sort the data in chronological order by `service_year`.
- For each of the two KPI columns, estimate a monotonic long-term trend that is suitable for modestly noisy yearly operations data.
- Compare the two slopes and select the KPI with the larger positive slope as the one worsening faster.
- If the two slopes are exactly equal, choose the alphabetically smaller KPI name.

Write `/root/output/reliability_metric_shift.csv` with exactly one data row and these columns in this order:

`metric_name,sen_slope_pct_points_per_year,p_value`

Requirements:
- `metric_name` must be either `late_departure_rate_pct` or `missed_connection_rate_pct`.
- `sen_slope_pct_points_per_year` is the selected KPI's slope in percentage points per year.
- `p_value` is the significance level for that KPI's monotonic trend.
- Round the slope to 3 decimal places and the p-value to 4 decimal places.

I only need that single CSV output.
