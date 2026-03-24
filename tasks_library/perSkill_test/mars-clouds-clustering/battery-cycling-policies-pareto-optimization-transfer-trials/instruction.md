# Transfer: Battery Cycling Policy Frontier

## Task

A battery research group ran repeated lab trials for several charging policies. Aggregate the accepted trial summaries, enforce the viability rules below, and write the final non-dominated recovered-capacity versus degradation trade-off set to `/root/battery_policy_frontier.csv`.

## Data

Files are in `/root/data/`:

- `policy_registry.csv`
  - Columns: `policy_id`, `charger_family`, `peak_c_rate`, `taper_soc`, `rest_minutes`, `upper_cutoff_v`
- `cycling_trial_summaries.jsonl`
  - One JSON object per line with fields: `policy_id`, `temperature_c`, `replicate_id`, `status`, `cycles_completed`, `recovered_capacity_mah`, `reference_capacity_mah`, `capacity_loss_mah`

`policy_id` is the join key. The registry fields are consistent within each policy.

## Trial Aggregation

Required temperature set:

- `10`
- `25`
- `40`

Use only trial rows where:

- `status == "accepted"`
- `cycles_completed >= 180`

For each remaining trial, compute:

```text
trial_recovered_capacity_pct =
100 * recovered_capacity_mah / reference_capacity_mah

trial_degradation_rate_pct_per_100_cycles =
100 * (capacity_loss_mah / reference_capacity_mah) * (100 / cycles_completed)
```

Then aggregate in two stages:

1. For each `(policy_id, temperature_c)`, require at least 2 remaining trials and take the arithmetic mean of the two trial metrics.
2. Discard the policy unless all three required temperatures remain after step 1.
3. For each surviving policy, compute:

   ```text
   recovered_capacity_pct =
   mean of the three temperature-level recovered-capacity means

   degradation_rate_pct_per_100_cycles =
   mean of the three temperature-level degradation-rate means
   ```

4. Keep only policies with `recovered_capacity_pct >= 92.0`.

## Duplicate Rounded Objective Rule

After rounding both policy-level objective values to 2 decimal places, multiple policies may land on the same objective pair. If that happens, keep only the lexicographically smallest `policy_id` and discard the others before computing the final frontier.

## Frontier

From the remaining policies, compute the Pareto frontier with these objectives:

- maximize `recovered_capacity_pct`
- minimize `degradation_rate_pct_per_100_cycles`

Use the unrounded policy-level objective values after duplicate-objective pruning when deciding Pareto optimality.

## Output

Write `/root/battery_policy_frontier.csv` with exactly these columns in this order:

```csv
recovered_capacity_pct,degradation_rate_pct_per_100_cycles,policy_id,charger_family,peak_c_rate,taper_soc,rest_minutes
```

Formatting requirements:

- round `recovered_capacity_pct` to 2 decimal places
- round `degradation_rate_pct_per_100_cycles` to 2 decimal places
- keep `taper_soc` and `rest_minutes` as integers
- sort rows by `recovered_capacity_pct` descending, then `degradation_rate_pct_per_100_cycles` ascending, then `policy_id`, `charger_family`, `peak_c_rate`, `taper_soc`, and `rest_minutes` ascending
