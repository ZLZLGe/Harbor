Energy demand often amplifies business-cycle swings because production schedules, building activity, and service-sector usage all react to changes in economic conditions. In this task you will work with a monthly U.S. panel that has already been assembled.

Goal: Using `/root/us_power_output_monthly.jsonl`, compare the cyclical volatility of commercial electricity demand and industrial production for 2010-01 through 2024-12, and write the volatility ratio to `/root/power-output-cycle-volatility.json`.

The JSONL file has one record per month with these fields:
- `month`
- `industrial_production_index`
- `commercial_power_gwh`
- `billing_days`
- `report_status`
- `season_band`

Requirements:
1. Use all rows in the file, covering 2010-01 through 2024-12.
2. The two target series are positive level variables, so take natural logs of both `industrial_production_index` and `commercial_power_gwh` before detrending.
3. Apply the Hodrick-Prescott filter with `lambda = 129600`.
4. Compute the sample standard deviation (`ddof = 1`) of each cyclical component.
5. Compute the volatility ratio as:
   - `power_to_output_volatility_ratio = commercial_power_cycle_std / industrial_production_cycle_std`
6. Write a JSON object to `/root/power-output-cycle-volatility.json` with exactly these numeric fields:
   - `commercial_power_cycle_std`
   - `industrial_production_cycle_std`
   - `power_to_output_volatility_ratio`
7. Round each reported value to 5 decimal places.

Example output:
```json
{
  "commercial_power_cycle_std": 0.03123,
  "industrial_production_cycle_std": 0.02456,
  "power_to_output_volatility_ratio": 1.27182
}
```
