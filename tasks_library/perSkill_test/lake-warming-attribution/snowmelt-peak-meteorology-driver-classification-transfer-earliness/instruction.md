The directory `/root/data/` contains annual observations for one alpine basin:

1. `snowmelt_peak_timing.csv`: observed annual snowmelt peak day of year (`peak_doy`)
2. `snow_energy_balance.csv`: spring energy and wind conditions
3. `basin_hydrology.csv`: spring runoff and rain-on-snow conditions
4. `winter_operations.csv`: managed winter-use pressure indicators

Create `/root/output/snowmelt_peak_driver.csv` with exactly one row and these columns:

1. `dominant_category`
2. `contribution_pct`

Use this workflow:

1. Merge all four files on `year`.
2. Create a derived variable `net_radiation_wm2 = shortwave_wm2 + longwave_wm2`.
3. Convert peak timing into an earliness metric with `peak_advance_days = max(peak_doy) - peak_doy`, so larger values mean an earlier annual snowmelt peak.
4. Use these candidate predictors for attribution:
   - `spring_air_temp_c`
   - `net_radiation_wm2`
   - `thawing_degree_days`
   - `spring_precip_mm`
   - `rain_on_snow_days`
   - `antecedent_runoff_mm`
   - `foehn_hours`
   - `ridge_gust_ms`
   - `snowmaking_withdrawal_mm`
   - `trail_grooming_days`
5. Classify the predictors into exactly these four categories:
   - Heat
   - Flow
   - Wind
   - Human
6. Z-score each predictor across years.
7. Build one category index per class by taking the mean of the z-scored predictors within that class.
8. Fit a linear regression using the four category indices to predict the z-scored `peak_advance_days`.
9. Treat only positive regression coefficients as contributions that advance the snowmelt peak date. Set negative coefficients to zero, normalize the remaining positive coefficients so they sum to 100, and report the category with the largest percentage.

Additional requirements:

- Keep the category names exactly as `Heat`, `Flow`, `Wind`, and `Human`.
- Use `net_radiation_wm2` instead of the raw `shortwave_wm2` and `longwave_wm2` columns in the attribution step.
- Round `contribution_pct` to 4 decimal places.
