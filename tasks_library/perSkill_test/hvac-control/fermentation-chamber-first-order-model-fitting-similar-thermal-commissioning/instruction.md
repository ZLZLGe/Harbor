A fermentation chamber was tested with one idle period followed by one constant-power heater step. Use `heating_step_log.csv` together with `chamber_profile.json` to identify the chamber's heating response and predict when the batch will enter the requested fermentation window.

Write exactly one file: `fermentation_model_fit.json`

Required JSON structure:

```json
{
  "batch_id": "saison-tank-07",
  "log_file": "heating_step_log.csv",
  "ambient_temperature_c": 18.705,
  "heater_power_percent": 45.0,
  "fitted_model": {
    "K": 0.1651,
    "tau_min": 14.52,
    "r_squared": 0.9997,
    "rmse_c": 0.0322
  },
  "predictions": {
    "target_band_c": [24.2, 24.8],
    "minutes_from_step_to_target_min": 19.55,
    "minutes_from_step_to_target_midpoint": 22.0,
    "minutes_from_step_to_target_max": 24.94
  }
}
```

Requirements:

- Compute `ambient_temperature_c` from the idle samples before the heater step.
- Estimate `K` and `tau_min` from the constant-power heating segment.
- `fitted_model` must contain numeric `K`, `tau_min`, `r_squared`, and `rmse_c`.
- `predictions.target_band_c` must exactly echo the target band from `chamber_profile.json`.
- The three prediction fields are the model-predicted minutes from heater-step onset to first reach the lower bound, midpoint, and upper bound of the target band.
- Use numeric JSON values, not strings.
