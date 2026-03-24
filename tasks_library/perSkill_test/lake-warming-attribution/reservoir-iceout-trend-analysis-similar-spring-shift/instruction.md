My data is in `/root/data/reservoir_ice_out.csv`. It contains one annual ice-out observation for the same reservoir in each season, but the rows are not sorted by year.

Please analyze whether the ice-out timing is shifting over time. Use the annual `ice_out_day_of_year` series in chronological order and calculate a monotonic trend that is appropriate for environmental observations with a few noisy years.

Write `/root/output/ice_out_trend.csv` with exactly one data row and these columns in this order:

`sen_slope_days_per_year,p_value,shift_direction`

Requirements:
- `sen_slope_days_per_year` is the long-term slope in days per year.
- `p_value` is the significance level for that trend.
- `shift_direction` should be `earlier` if the slope is negative, `later` if the slope is positive, and `no_change` only if the slope is exactly zero.
- Round the slope to 3 decimal places and the p-value to 4 decimal places.

I only need that single CSV output.
