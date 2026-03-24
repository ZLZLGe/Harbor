# Transfer: Coastal Sensor Procurement Frontier

## Task

A coastal resilience team is comparing pre-bid buoy packages for a shoreline monitoring rollout. Evaluate each candidate bundle, discard proposals that miss the minimum shoreline coverage requirement, and write the final non-dominated coverage/cost trade-off set to `/root/procurement_frontier.csv`.

## Data

Files are in `/root/data/`:

- `bundle_components.csv`
  - Columns: `bundle_id`, `vendor`, `buoy_model`, `sensor_suite`, `component`, `quantity`, `unit_cost_usd`
- `bundle_operations.csv`
  - Columns: `bundle_id`, `shoreline_km`, `uptime_rate`, `data_return_rate`, `annual_support_usd`, `annual_permit_usd`, `replacement_events_3yr`, `replacement_cost_usd`

`bundle_id` is the join key. The fields `vendor`, `buoy_model`, and `sensor_suite` are consistent within each bundle in `bundle_components.csv`.

## Bundle Scoring

For each `bundle_id`:

1. Compute `procurement_capex_usd` as the sum of `quantity * unit_cost_usd` across all component rows in `bundle_components.csv`.
2. Compute `expected_annual_coverage_km` as:

   ```
   shoreline_km * uptime_rate * data_return_rate
   ```

3. Discard the bundle if `expected_annual_coverage_km < 170`.
4. Compute `total_3yr_cost_usd` as:

   ```
   procurement_capex_usd
   + 3 * (annual_support_usd + annual_permit_usd)
   + replacement_events_3yr * replacement_cost_usd
   ```

## Frontier

From the surviving bundles, compute the Pareto frontier with these objectives:

- maximize `expected_annual_coverage_km`
- minimize `total_3yr_cost_usd`

Use the unrounded numeric values when deciding Pareto optimality.

## Output

Write `/root/procurement_frontier.csv` with exactly these columns in this order:

```csv
expected_annual_coverage_km,total_3yr_cost_usd,bundle_id,vendor,buoy_model,sensor_suite
```

Formatting requirements:

- round `expected_annual_coverage_km` to 2 decimal places
- round `total_3yr_cost_usd` to 2 decimal places
- sort rows by `expected_annual_coverage_km` descending, then `total_3yr_cost_usd` ascending, then `bundle_id`, `vendor`, `buoy_model`, and `sensor_suite` ascending
