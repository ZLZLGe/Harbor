You are given a noisy open-loop heater step test from a benchtop incubator. The heater stayed off during the baseline period and then switched to a fixed duty cycle.

Use `/root/incubator_step_test.csv` and `/root/incubator_run_info.json` to identify a first-order thermal model for the heater-on segment:

`T(t) = T_ambient + K * u * (1 - exp(-(t - t_step) / tau))`

Where:
- `T_ambient` is the ambient chamber temperature in C
- `u` is the fixed heater percentage during the step
- `K` is the steady-state gain in C per percent heater
- `tau` is the thermal time constant in seconds

Then estimate the steady heater percentage required to hold the target culture temperature from the run info file.

Write `/root/incubator_fit_report.json` with this structure:

```json
{
  "experiment_id": "bench-incubator-step-17a",
  "input_file": "incubator_step_test.csv",
  "ambient_temperature_c": 23.4,
  "target_temperature_c": 37.0,
  "heater_step_percent": 55.0,
  "step_start_time_s": 120.0,
  "samples_used": 57,
  "model": {
    "gain_c_per_percent": 0.255,
    "time_constant_s": 480.0,
    "r_squared": 0.998,
    "rmse_c": 0.12
  },
  "predicted_equilibrium_at_step_c": 37.43,
  "required_hold_heater_percent": 53.33
}
```

Requirements:
- Fit the model using the heater-on portion of the log.
- `samples_used` must equal the number of heater-on samples included in the fit.
- `predicted_equilibrium_at_step_c` should be the fitted steady-state temperature for the recorded heater step.
- `required_hold_heater_percent` should be the steady heater percentage predicted to maintain the target temperature.
