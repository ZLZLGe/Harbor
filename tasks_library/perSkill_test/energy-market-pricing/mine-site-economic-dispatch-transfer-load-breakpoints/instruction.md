You are supporting the power superintendent of a remote mining complex that supplies its own process load with an on-site thermal fleet. The superintendent wants a breakpoint study across several standalone production load blocks to understand when the standby turbine meaningfully enters the least-cost dispatch.

The environment contains three input files:
- `thermal_units.csv`: one row per generating unit with its minimum output, maximum output, and hourly cost-curve coefficients.
- `load_blocks.csv`: the production load blocks to study. Treat every block as an independent dispatch problem.
- `study_config.json`: identifies the standby unit and the dispatch threshold that defines the breakpoint.

For each load block, compute the least-cost dispatch subject to:
1. Total scheduled generation must equal that block's `load_mw`.
2. Each unit's output must stay between `pmin_mw` and `pmax_mw`.
3. The hourly production cost of a unit is `cost_quadratic * output_mw^2 + cost_linear * output_mw + cost_fixed`.

Use these reporting rules:
- Keep `load_blocks` in the same order as the input file.
- Keep each block's `dispatch` list in the same order as `thermal_units.csv`.
- `total_cost_dollars_per_hour` is the minimum total hourly production cost for that block.
- `marginal_system_cost_dollars_per_mwh` is the increase in minimum total hourly production cost if that block's load is increased by exactly 1 MW while unit limits and cost curves stay unchanged.
- The breakpoint is the first listed load block for which the standby unit's dispatch is strictly greater than the threshold in `study_config.json`.
- Round every numeric value in the JSON to 2 decimal places.

Create `breakpoint_study.json` with this structure:

```json
{
  "load_blocks": [
    {
      "block_id": "night_ventilation",
      "load_mw": 150.0,
      "total_cost_dollars_per_hour": 2130.38,
      "marginal_system_cost_dollars_per_mwh": 15.86,
      "dispatch": [
        {
          "unit_id": "waste_heat_recovery",
          "output_mw": 55.0
        }
      ]
    }
  ],
  "standby_breakpoint": {
    "unit_id": "standby_turbine",
    "threshold_mw": 10.0,
    "first_block_id": "full_blend_train",
    "first_load_mw": 236.0,
    "dispatch_mw": 11.0
  }
}
```
