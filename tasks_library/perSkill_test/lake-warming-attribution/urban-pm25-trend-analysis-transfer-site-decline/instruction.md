My data is in `/root/data/urban_pm25_observations.csv`. Each row is a PM2.5 reading from one monitoring site during a high-pollution event, with columns `site_id`, `observation_date`, and `pm25_ug_m3`.

Please determine which site shows the steepest statistically significant decline in its yearly high-pollution PM2.5 level.

Use this workflow:
- Parse `observation_date` to calendar year.
- For each `site_id` and year, calculate `annual_high_pollution_pm25` as the mean of the three highest `pm25_ug_m3` values observed for that site in that year.
- For each site, sort those yearly summaries by year and estimate a monotonic trend that is appropriate for noisy environmental time series.
- Keep only sites with a negative slope and `p_value < 0.05`.
- From those qualifying sites, select the site with the most negative slope. If two sites have exactly the same slope, choose the alphabetically smaller `site_id`.

Write `/root/output/pm25_decline_leader.csv` with exactly one data row and these columns in this order:

`site_id,sen_slope_peak_pm25_per_year,p_value,years_used`

Requirements:
- `sen_slope_peak_pm25_per_year` is the long-term slope for the yearly high-pollution summaries.
- `p_value` is the significance level for that trend.
- `years_used` is the number of yearly summaries used for the winning site.
- Round the slope to 3 decimal places and the p-value to 4 decimal places.

I only need that single CSV output.
