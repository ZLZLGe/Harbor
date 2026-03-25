You are scheduling a remote island microgrid for the next 24 hours after a delayed diesel delivery.

Read these input files:

- `/root/dispatch_requirements.json`
- `/root/generator_fleet.csv`
- `/root/hourly_load.csv`

Assume every listed generator is available for every hour, with no startup, shutdown, or ramping model. For each hour, choose generator outputs that satisfy:

1. Total generation exactly equals the hourly load.
2. For each generator, `min_output_MW <= output_MW <= max_output_MW`.
3. Total fuel used across all 24 hours does not exceed `daily_fuel_budget_liters`.

Among all feasible 24-hour schedules, minimize total variable operating cost:

- Hourly cost contribution of one generator = `output_MW * variable_cost_dollars_per_MWh`

Write `/root/microgrid_schedule.csv` with exactly this header and column order:

```text
hour,load_MW,pier_1_MW,ridge_2_MW,cove_3_MW,airport_4_MW,total_generation_MW,hourly_fuel_liters,cumulative_fuel_liters
```

Output requirements:

- Write one row for each row of `hourly_load.csv`, in the same order.
- Copy `hour` and `load_MW` from the load input.
- Each generator column must contain that unit's dispatch for the hour.
- `total_generation_MW` must equal the sum of the four generator output columns.
- `hourly_fuel_liters` must equal the hourly sum of `output_MW * fuel_burn_liters_per_MWh` across all generators.
- `cumulative_fuel_liters` must be the running total of `hourly_fuel_liters`.
- The final `cumulative_fuel_liters` value must be less than or equal to the budget in `dispatch_requirements.json`.
- Use CSV numeric values for all MW and fuel fields.
