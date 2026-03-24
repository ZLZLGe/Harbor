A brine blending skid was logged during a valve step test. Use `mixing_run_manifest.json` together with `outlet_concentration_trace.tsv` to identify an equivalent concentration-response model for the outlet stream and predict when the batch first enters, then leaves, the acceptable concentration band.

Write exactly one file: `mixing_tank_fit.json`

Required JSON structure:

```json
{
  "trial_id": "brine-skid-2/qualification-step-03",
  "log_file": "outlet_concentration_trace.tsv",
  "baseline_concentration_g_per_l": 5.166,
  "valve_step_percent_open": 14.0,
  "fitted_model": {
    "gain_g_per_l_per_pct_open": 0.6714,
    "tau_s": 42.15,
    "steady_state_concentration_g_per_l": 14.565,
    "r_squared": 0.99988,
    "rmse_g_per_l": 0.0284
  },
  "qualification_window": {
    "target_band_g_per_l": [12.6, 13.1],
    "time_to_enter_band_s": 65.96,
    "time_to_leave_band_s": 78.34,
    "time_in_band_s": 12.37
  }
}
```

Requirements:

- Compute `baseline_concentration_g_per_l` from samples strictly before the valve step.
- Use `valve_step_percent_open` from `mixing_run_manifest.json` as the step amplitude for the fitted model.
- Estimate `gain_g_per_l_per_pct_open` and `tau_s` from concentration samples at or after the step.
- `steady_state_concentration_g_per_l` must be consistent with the fitted model and the valve step amplitude.
- `fitted_model` must contain numeric `gain_g_per_l_per_pct_open`, `tau_s`, `steady_state_concentration_g_per_l`, `r_squared`, and `rmse_g_per_l`.
- `qualification_window.target_band_g_per_l` must exactly echo the target band from `mixing_run_manifest.json`.
- `time_to_enter_band_s` is the model-predicted time from the valve step to first reach the lower concentration limit.
- `time_to_leave_band_s` is the model-predicted time from the valve step to first reach the upper concentration limit.
- `time_in_band_s` is the difference between those two predicted times.
- Use numeric JSON values, not strings.
