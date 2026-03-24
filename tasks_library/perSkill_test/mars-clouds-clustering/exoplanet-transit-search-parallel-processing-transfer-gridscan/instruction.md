# Transfer | Exoplanet Transit Template Scan

## Task

You are given normalized stellar light curves plus a validation catalog that marks which stars truly host a transit-like signal.

Evaluate the full box-transit template grid below and write the top 20 parameter combinations to `/root/transit_template_rankings.csv`.

## Data

Files are in `/root/data/`:

- `light_curves.csv`
  - `star_id`
  - `time_days`
  - `flux`
  - `flux_err`
- `validation_catalog.csv`
  - `star_id`
  - `is_transiting`

Use every `star_id` listed in `validation_catalog.csv`.

## Template Grid

Evaluate every combination of:

- `period_days`: `2.0, 2.5, 3.0, 3.5, 4.0, 4.5`
- `duration_hours`: `2, 3, 4, 5`
- `depth_ppt`: `6, 8, 10, 12, 14`
- `epoch_hours`: `0, 6, 12, 18`

## Per-star Evaluation

For one template and one star:

1. Fold the observation times by `period_days`.
2. A sample is in transit when:

   ```text
   ((time_days - epoch_hours / 24) mod period_days) < duration_hours / 24
   ```

3. Build a box model:
   - model flux = `1 - depth_ppt / 1000` inside transit
   - model flux = `1` outside transit
4. Compute:

   ```text
   flat_chi2 = sum(((flux - 1) / flux_err)^2)
   template_chi2 = sum(((flux - model_flux) / flux_err)^2)
   delta_chi2 = max(flat_chi2 - template_chi2, 0)
   detection_score = delta_chi2 / N_obs
   ```

   where `N_obs` is the number of rows for that star in `light_curves.csv`.

## Aggregation

For each parameter combination:

- positive stars are rows with `is_transiting = 1`
- negative stars are rows with `is_transiting = 0`
- `mean_detection_score` is the arithmetic mean of `detection_score` over positive stars
- a negative star counts as a false alarm when its `delta_chi2 >= 20.0`
- `false_alarm_rate` is the fraction of negative stars that count as false alarms
- `composite_score = mean_detection_score - 0.75 * false_alarm_rate`

## Ranking And Output

Rank all parameter combinations by:

1. `composite_score` descending
2. `mean_detection_score` descending
3. `false_alarm_rate` ascending
4. `period_days` ascending
5. `duration_hours` ascending
6. `depth_ppt` ascending
7. `epoch_hours` ascending

Write only the top 20 rows to `/root/transit_template_rankings.csv` with this exact header:

```csv
rank,composite_score,mean_detection_score,false_alarm_rate,period_days,duration_hours,depth_ppt,epoch_hours
```

Formatting rules:

- `rank` is `1` through `20`
- round `composite_score`, `mean_detection_score`, and `false_alarm_rate` to 6 decimal places
- round `period_days` to 1 decimal place
- keep `duration_hours`, `depth_ppt`, and `epoch_hours` as integers
