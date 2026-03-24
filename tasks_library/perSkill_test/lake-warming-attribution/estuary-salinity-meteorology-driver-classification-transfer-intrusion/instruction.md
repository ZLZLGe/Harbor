The directory `/root/data/` contains dry-season estuary observations:

1. `salinity_transects.csv`: station-by-station salinity measurements from repeated dry-season transect surveys
2. `estuary_driver_conditions.csv`: annual dry-season forcing and development indicators for the same estuary

Create `/root/output/salinity_intrusion_driver.csv` with exactly one row and these columns:

1. `intrusion_status`
2. `sen_slope_km_per_year`
3. `dominant_category`
4. `contribution_pct`

Use this workflow:

1. From `salinity_transects.csv`, calculate one `salt_front_km` value for each `year` and `survey_id` by taking the maximum `distance_km` where `salinity_psu >= 1.0`.
2. Aggregate the survey-level salt-front distances to yearly dry-season intrusion severity by taking the median `salt_front_km` within each year.
3. Quantify whether intrusion is worsening by calculating the Sen slope of yearly intrusion severity against `year` and the two-sided Mann-Kendall p-value for the yearly intrusion series.
4. Set `intrusion_status` to `worsening` only when the Sen slope is positive and `p_value < 0.05`. Otherwise set it to `not_worsening`.
5. Merge the yearly intrusion-severity table with `estuary_driver_conditions.csv` on `year`.
6. Create a derived variable `net_radiation_wm2 = shortwave_wm2 + longwave_wm2`.
7. Use these candidate predictors for attribution:
   - `air_temp_c`
   - `sea_surface_temp_c`
   - `net_radiation_wm2`
   - `river_discharge_m3s`
   - `dry_season_rain_mm`
   - `tidal_prism_index`
   - `along_estuary_wind_ms`
   - `mean_pressure_hpa`
   - `channel_dredging_m3`
   - `freshwater_withdrawal_mcm`
8. Classify the predictors into exactly these four categories:
   - Heat
   - Flow
   - Wind
   - Human
9. Z-score each predictor across years.
10. Build one category index per class by taking the median of the z-scored predictors assigned to that category.
11. Z-score the yearly intrusion severity series.
12. Fit a linear regression with an intercept using the four category indices to predict the z-scored yearly intrusion severity.
13. For each category, fit a reduced regression that excludes only that category. Define that category's raw contribution score as `max(0, SSE_without_category - SSE_full)`.
14. Normalize the four raw contribution scores so they sum to 100, then report the largest percentage as `contribution_pct` and its category as `dominant_category`.

Additional requirements:

- Keep the category names exactly as `Heat`, `Flow`, `Wind`, and `Human`.
- Use `net_radiation_wm2` in the attribution step instead of the raw radiation columns.
- Round `sen_slope_km_per_year` and `contribution_pct` to 4 decimal places.
