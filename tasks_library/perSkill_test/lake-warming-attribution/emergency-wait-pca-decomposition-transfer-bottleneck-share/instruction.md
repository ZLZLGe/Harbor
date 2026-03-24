The folder `/root/data/` contains one emergency-department operating day per row, keyed by `day_id`, across two files:

- `ed_operational_metrics.csv`
- `ed_wait_targets.csv`

The response variable is `p90_wait_minutes` from `ed_wait_targets.csv`. The 12 driver variables in `ed_operational_metrics.csv` belong to four operational categories:

- Arrival Pressure: `arrivals_per_hour`, `ambulance_share_pct`, `triage_queue_min`
- Bed Flow: `boarded_patients`, `bed_clean_turnaround_min`, `admit_to_bed_min`
- Diagnostics: `lab_tat_min`, `ct_tat_min`, `consult_callback_min`
- Staffing: `md_hours_per_100_visits`, `rn_hours_per_100_visits`, `overflow_bay_open_pct`

Merge the two files on `day_id`, use all 12 driver variables together in one global dimensionality-reduction step, keep 4 factors, and apply an orthogonal rotation so the factors are interpretable.

Assign each rotated factor to the category whose variables have the largest mean absolute loading on that factor.

Then regress `p90_wait_minutes` on the rotated factor scores. For each category, define its raw contribution as the variance of that category's fitted signal:

`variance(sum(beta_factor * factor_score))`

where the sum runs over all factors assigned to that category. Normalize the four raw contributions so their shares sum to 100.

Write `/root/output/ed_bottleneck_share.csv` with exactly these columns:

- `category`
- `share_pct`

Only include the single dominant category as one row, with `share_pct` reported as a percentage.
