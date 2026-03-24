My data is in `/root/data/assembly_quality_monthly.csv`. Each row is one monthly production summary for an electronics assembly line, with columns:

- `line_code`
- `month`
- `line_role`
- `units_completed`
- `defects_found`

I only care about the flagship line, which is identified by `line_role = flagship`. The rows are not sorted by month.

Please determine whether the flagship line's quality is improving or worsening over time.

Use this workflow:
- Keep only the flagship rows.
- Sort them in chronological order by `month`.
- For each month, compute `defect_rate_pct = defects_found / units_completed * 100`.
- Estimate a monotonic long-term trend that is suitable for a slightly noisy operational time series.
- Interpret the direction as `improving` if the slope is negative, `worsening` if the slope is positive, and `stable` only if the slope is exactly zero.

Write `/root/output/defect_rate_trend.csv` with exactly one data row and these columns in this order:

`sen_slope_pct_points_per_month,p_value,quality_direction`

Requirements:
- `sen_slope_pct_points_per_month` is the monthly slope of the defect rate in percentage points per month.
- `p_value` is the significance level for that trend.
- Round the slope to 4 decimal places and the p-value to 4 decimal places.

I only need that single CSV output.
