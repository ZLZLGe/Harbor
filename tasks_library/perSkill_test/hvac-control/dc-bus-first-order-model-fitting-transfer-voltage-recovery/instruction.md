An auxiliary load bank was disconnected from a rectifier cabinet, and the DC bus voltage recovery was logged around the switching instant. Use `dc_bus_event.json` together with `voltage_recovery_samples.jsonl` to fit an equivalent recovery model for the bus voltage.

Write exactly one file: `dc_bus_fit.json`

Required JSON structure:

```json
{
  "event_id": "rectifier-bay-3/load-release-17",
  "samples_file": "voltage_recovery_samples.jsonl",
  "pre_event_voltage_v": 371.815,
  "released_load_a": 18.0,
  "fitted_model": {
    "gain_v_per_a": 0.421661,
    "tau_ms": 7.584729,
    "steady_state_voltage_v": 379.404898,
    "r_squared": 0.999922,
    "rmse_v": 0.017914
  },
  "recovery_metrics": {
    "target_fraction": 0.95,
    "time_to_95_ms": 22.721818,
    "voltage_at_95_v": 379.025403
  }
}
```

Requirements:

- Compute `pre_event_voltage_v` from samples strictly before the switch event.
- Use the released current in `dc_bus_event.json` as the step amplitude for the fitted model.
- Estimate `gain_v_per_a` and `tau_ms` from the voltage samples at or after the switch event.
- `steady_state_voltage_v` must be consistent with the fitted model and the released current.
- `fitted_model` must contain numeric `gain_v_per_a`, `tau_ms`, `steady_state_voltage_v`, `r_squared`, and `rmse_v`.
- `recovery_metrics.target_fraction` must exactly echo `recovery_target_fraction` from `dc_bus_event.json`.
- `time_to_95_ms` is the model-predicted time from the switch event to first reach the requested fraction of the final voltage rise.
- `voltage_at_95_v` is the corresponding voltage threshold implied by the fitted model.
- Use numeric JSON values, not strings.
