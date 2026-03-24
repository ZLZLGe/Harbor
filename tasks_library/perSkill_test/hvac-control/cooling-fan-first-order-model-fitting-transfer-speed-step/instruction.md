A supply-air cooling fan was logged during a commanded PWM step from one steady operating point to a higher one. Use `fan_step_profile.toml` together with `fan_speed_trace.csv` to identify an equivalent speed-response model and predict when the fan reaches the requested fractions of its total speed rise.

Write exactly one file: `fan_speed_fit.json`

Required JSON structure:

```json
{
  "run_id": "ahu-bay-2/fan-step-06",
  "samples_file": "fan_speed_trace.csv",
  "baseline_speed_rpm": 1470.69,
  "pwm_step_percent": 24.0,
  "fitted_model": {
    "gain_rpm_per_pwm_pct": 58.82,
    "tau_s": 2.84,
    "steady_state_speed_rpm": 2882.37,
    "r_squared": 0.99973,
    "rmse_rpm": 5.73
  },
  "response_predictions": {
    "target_percentages_of_speed_rise": [80.0, 95.0],
    "time_to_targets_s": {
      "p80": 4.57,
      "p95": 8.51
    },
    "predicted_target_speeds_rpm": {
      "p80": 2600.03,
      "p95": 2811.79
    }
  }
}
```

Requirements:

- Compute `baseline_speed_rpm` from samples strictly before the PWM step time in `fan_step_profile.toml`.
- `pwm_step_percent` must be `pwm_after_percent - pwm_before_percent` from `fan_step_profile.toml`.
- Estimate `gain_rpm_per_pwm_pct` and `tau_s` from the speed samples at or after the PWM step.
- `steady_state_speed_rpm` must be consistent with `baseline_speed_rpm`, `gain_rpm_per_pwm_pct`, and `pwm_step_percent`.
- `fitted_model` must contain numeric `gain_rpm_per_pwm_pct`, `tau_s`, `steady_state_speed_rpm`, `r_squared`, and `rmse_rpm`.
- `response_predictions.target_percentages_of_speed_rise` must exactly echo `target_percentages_of_speed_rise` from `fan_step_profile.toml`.
- `time_to_targets_s.p80` and `time_to_targets_s.p95` are the model-predicted seconds from the PWM step to first reach 80% and 95% of the total speed rise.
- `predicted_target_speeds_rpm.p80` and `predicted_target_speeds_rpm.p95` are the corresponding speed thresholds implied by the fitted model.
- Use numeric JSON values, not strings.
