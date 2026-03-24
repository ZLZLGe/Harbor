The file `/root/data/reservoir_monthly_monitoring.csv` contains monthly observations for one reservoir during the warm season (May through September) from 2010 to 2023.

Create `/root/output/evaporation_driver_summary.csv` with exactly one row and these columns:

1. `trend_label`
2. `sen_slope_mm_day_per_year`
3. `p_value`
4. `dominant_category`
5. `contribution_pct`

Use this workflow:

1. Aggregate the monthly data to yearly warm-season values by taking the mean of every numeric field within each year.
2. Create a derived variable `net_radiation_wm2 = shortwave_wm2 + longwave_wm2`.
3. Determine whether warm-season evaporation intensified over time by calculating:
   - the Sen slope of yearly `evaporation_mm_day` against `year`
   - the two-sided Mann-Kendall p-value for the yearly `evaporation_mm_day` series
4. Set `trend_label` to `intensified` only when the Sen slope is positive and `p_value < 0.05`. Otherwise set it to `not_intensified`.
5. Classify the candidate predictors into exactly these four categories:
   - Heat
   - Flow
   - Wind
   - Human
6. Build one category index per class by z-scoring each predictor across years and then taking the mean of the z-scored predictors within that class.
7. Fit a linear regression using the four category indices to predict yearly warm-season `evaporation_mm_day`.
8. Convert the absolute values of the four regression coefficients into percentages that sum to 100. Report the category with the largest percentage as `dominant_category`, and report that percentage as `contribution_pct`.

Additional requirements:

- Use all candidate predictors in the file except `year`, `month`, and `evaporation_mm_day`.
- Keep the category names exactly as `Heat`, `Flow`, `Wind`, and `Human`.
- Round `sen_slope_mm_day_per_year`, `p_value`, and `contribution_pct` to 4 decimal places in the output CSV.
