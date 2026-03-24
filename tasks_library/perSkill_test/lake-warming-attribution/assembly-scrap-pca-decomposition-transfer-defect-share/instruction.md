The folder `/root/data/` contains one row per production shift, keyed by `shift_id`, across five files:

- `line_environment.csv`
- `machine_condition.csv`
- `incoming_material.csv`
- `line_load.csv`
- `scrap_quality.csv`

The response variable is `scrap_rate_pct` from `scrap_quality.csv`. The 12 driver variables belong to four categories:

- Climate: `ambient_temp_c`, `ambient_humidity_pct`, `dew_point_c`
- Vibration: `spindle_vibration_mm_s`, `fixture_shock_g`, `bearing_temp_c`
- Material: `incoming_thickness_cv`, `supplier_mix_delta_pct`, `burr_rate_pct`
- Load: `cycle_time_sec`, `overtime_minutes`, `queue_length_units`

Merge the five files on `shift_id`, use all 12 driver variables together in one global dimensionality-reduction step, keep 4 factors, and apply an orthogonal rotation so the factors are interpretable.

Assign each rotated factor to the category whose variables have the largest mean absolute loading on that factor.

Then regress `scrap_rate_pct` on the rotated factor scores. Define each category's raw contribution as:

`sum(abs(beta_factor) * variance(factor_score))`

where the sum runs over all factors assigned to that category. Normalize the four raw contributions so their shares sum to 100.

Write `/root/output/scrap_defect_share.csv` with exactly these columns:

- `category`
- `share_pct`

Only include the single dominant category as one row, with `share_pct` reported as a percentage.
