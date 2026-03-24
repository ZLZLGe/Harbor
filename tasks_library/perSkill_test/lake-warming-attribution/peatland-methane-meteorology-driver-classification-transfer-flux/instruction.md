The directory `/root/data/` contains restored peatland observations:

1. `methane_flux_campaigns.csv`: zone-level methane flux estimates for repeated growing-season chamber campaigns
2. `peatland_hydroclimate.csv`: annual peatland heat, water, and wind conditions
3. `restoration_actions.csv`: annual restoration-management indicators

Create `/root/output/methane_flux_driver.csv` with exactly one row and these columns:

1. `flux_trend`
2. `sen_slope_mg_m2_day_per_year`
3. `dominant_category`
4. `contribution_pct`

Use this workflow:

1. From `methane_flux_campaigns.csv`, calculate one site-scale methane flux for each `year` and `campaign_id` by taking the area-weighted mean of `methane_flux_mg_m2_day` using `zone_area_frac`.
2. Aggregate the campaign-level site fluxes to yearly methane flux by taking the mean across campaigns within each year.
3. Calculate the Sen slope of yearly methane flux against `year`.
4. Set `flux_trend` to `increasing` when the Sen slope is positive. Otherwise set it to `not_increasing`.
5. Merge the yearly methane-flux table with `peatland_hydroclimate.csv` and `restoration_actions.csv` on `year`.
6. Create a derived variable `net_radiation_wm2 = shortwave_wm2 + longwave_wm2`.
7. Use these candidate predictors for attribution:
   - `soil_temp_5cm_c`
   - `peat_temp_15cm_c`
   - `net_radiation_wm2`
   - `water_table_anomaly_cm`
   - `inundation_days`
   - `catchment_inflow_mm`
   - `mean_wind_ms`
   - `gust_hours`
   - `ditch_blocks_installed`
   - `rewetted_margin_ha`
8. Classify the predictors into exactly these four categories:
   - Heat
   - Flow
   - Wind
   - Human
9. Z-score each predictor across years.
10. Build one category index per class by taking the median of the z-scored predictors assigned to that category.
11. Convert the yearly methane-flux series into year-to-year increments with `flux_increment = methane_flux_mg_m2_day.diff()`.
12. For each category, calculate `category_increment = category_index.diff()` and compute its Pearson correlation with `flux_increment` over the aligned years.
13. Define each category's raw contribution score as `max(0, correlation)^2`.
14. Normalize the four raw contribution scores so they sum to 100, then report the largest percentage as `contribution_pct` and its category as `dominant_category`.

Additional requirements:

- Keep the category names exactly as `Heat`, `Flow`, `Wind`, and `Human`.
- Use `net_radiation_wm2` in the attribution step instead of the raw radiation columns.
- Round `sen_slope_mg_m2_day_per_year` and `contribution_pct` to 4 decimal places.
