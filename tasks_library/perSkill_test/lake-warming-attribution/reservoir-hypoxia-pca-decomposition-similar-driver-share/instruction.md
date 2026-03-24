The file `/root/data/summer_hypoxia_panel.csv` contains one summer season per year for a reservoir. The response variable is `summer_hypoxia_days`, and the 12 driver variables are grouped into four domain categories:

- Thermal: `surface_temp_c`, `stratification_days`, `schmidt_stability`
- Flow: `residence_time_days`, `drawdown_m`, `flushing_ratio`
- Nutrient: `tp_load_t`, `srf_p_mg_l`, `chlorophyll_a_ug_l`
- Shoreline: `bulkhead_pct`, `dock_density_km`, `impervious_shoreline_ha`

Use all 12 driver variables together in one global dimensionality-reduction step, keep 4 factors, apply an orthogonal rotation for interpretability, and use the rotated factor scores to quantify each category's contribution to `summer_hypoxia_days`.

Define each category's contribution as the drop in fitted R-squared after removing the factor(s) assigned to that category. Then normalize the four positive contributions so their shares sum to 100.

Write `/root/output/hypoxia_driver_share.csv` with exactly these columns:

- `category`
- `share_pct`

Only include the single dominant category, as one row, with `share_pct` reported as a percentage.
