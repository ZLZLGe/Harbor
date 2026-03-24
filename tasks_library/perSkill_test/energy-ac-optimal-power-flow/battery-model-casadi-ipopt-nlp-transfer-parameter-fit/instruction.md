You are calibrating a first-order RC equivalent-circuit model for a lithium-ion cell characterization bench. Use `battery-rc-model.md` together with `battery_experiment_case.json` to fit the six temperature-aware parameters on the training segments, then evaluate the fitted model on the validation segments and write `/root/battery_model_fit_report.json`.

The input file uses `row_schema = ["step", "time_s", "dt_s", "current_a", "temperature_c", "soc", "voltage_v", "ocv_v"]` for every row in every segment.

Your report must be valid JSON and follow this structure exactly:

```json
{
  "summary": {
    "scenario_id": "nmc_pulse_rc_temperature_fit",
    "solver_status": "optimal",
    "objective_value_v2": 0.00001460,
    "train_sample_count": 62,
    "validation_sample_count": 54,
    "train_rmse_v": 0.00049,
    "validation_rmse_v": 0.00069,
    "max_abs_residual_v": 0.00120,
    "minimum_relative_bound_margin": 0.28
  },
  "identified_parameters": {
    "r0_ref_ohm": 0.0142,
    "r0_temp_coeff_per_c": -0.0120,
    "r1_ref_ohm": 0.0215,
    "r1_temp_coeff_per_c": -0.0180,
    "c1_ref_f": 2550.0,
    "c1_temp_coeff_per_c": 0.0090
  },
  "parameter_bound_margins": [
    {
      "name": "r0_ref_ohm",
      "value": 0.0142,
      "lower_margin": 0.0062,
      "upper_margin": 0.0158,
      "relative_margin": 0.2818
    }
  ],
  "residual_statistics": {
    "train_mae_v": 0.00040,
    "train_mean_bias_v": -0.00001,
    "validation_mae_v": 0.00058,
    "validation_mean_bias_v": 0.00002
  },
  "train_segments": [
    {
      "segment_id": "train_mild_25c",
      "sample_count": 32,
      "rmse_v": 0.00049,
      "mae_v": 0.00041,
      "max_abs_residual_v": 0.00093,
      "final_rc_voltage_v": 0.0114
    }
  ],
  "validation_segments": [
    {
      "segment_id": "validation_cool_pulse",
      "sample_count": 26,
      "rmse_v": 0.00064,
      "mae_v": 0.00055,
      "mean_bias_v": -0.00006,
      "max_abs_residual_v": 0.00116
    }
  ],
  "largest_residuals": [
    {
      "rank": 1,
      "segment_id": "validation_mixed_recovery",
      "step": 23,
      "time_s": 138.0,
      "residual_v": 0.00120,
      "abs_residual_v": 0.00120,
      "measured_voltage_v": 3.85636,
      "modeled_voltage_v": 3.85756,
      "temperature_c": 28.0899,
      "current_a": -0.9
    }
  ]
}
```

Additional requirements:

- `identified_parameters` must contain exactly the six parameters defined in `parameter_bounds`.
- `parameter_bound_margins` must list those same six parameters in the same order as `parameter_bounds`.
- `train_segments` must follow `train_segment_ids` from `battery_experiment_case.json`.
- `validation_segments` must follow `validation_segment_ids` from `battery_experiment_case.json`.
- `largest_residuals` must contain exactly the number of rows requested by `top_residual_count`, sorted by descending `abs_residual_v`, then by `segment_id`, then by `step`.
- Use residual sign convention `modeled_voltage_v - measured_voltage_v`.
- `objective_value_v2` must be the sum of squared residuals over the training segments only.
