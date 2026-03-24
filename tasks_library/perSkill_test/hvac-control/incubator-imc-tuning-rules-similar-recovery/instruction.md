You need to produce exactly one file: `incubator_controller_bundle.json`.

Use the provided incubator recovery model in `incubator_case.json` and validate your controller with `incubator_recovery_sim.py`. The chamber has already cooled down after a door-open event and starts from `31.2C`; your target is to recover and hold `37.0C`.

Treat the plant as a first-order process with:

- `K = process_gain_c_per_percent`
- `tau = time_constant_s`

Choose a positive `lambda_s` for the desired closed-loop speed, then compute the controller with these exact rules:

- `Kp = tau / (K * lambda_s)`
- `Ki = Kp / tau`
- `Kd = 0.0`

After choosing `lambda_s`, run the provided simulator helpers to build the output:

- Use `simulate_pi_controller(config_path, Kp, Ki)` from `incubator_recovery_sim.py` to generate `closed_loop_trace`.
- Use `compute_metrics(trace, setpoint_c, settling_band_c, steady_state_window_s, dt_s)` from the same file to generate `performance_summary`.

Copy the scenario values in your JSON from `incubator_case.json` exactly for the fields listed below. Store the full result in `incubator_controller_bundle.json`.

Required JSON structure:

```json
{
  "scenario": {
    "setpoint_c": 37.0,
    "initial_temp_c": 31.2,
    "ambient_temp_c": 23.5,
    "process_gain_c_per_percent": 0.26,
    "time_constant_s": 70.0,
    "duration_s": 420.0,
    "dt_s": 1.0
  },
  "controller": {
    "type": "PI",
    "Kp": 10.0,
    "Ki": 0.15,
    "Kd": 0.0,
    "lambda_s": 25.0
  },
  "closed_loop_trace": [
    {
      "time_s": 1.0,
      "temperature_c": 31.5,
      "heater_power_pct": 60.0,
      "error_c": 5.5
    }
  ],
  "performance_summary": {
    "settling_time_s": 200.0,
    "overshoot_c": 0.1,
    "steady_state_error_c": 0.05,
    "peak_temperature_c": 37.1,
    "final_temperature_c": 37.0
  },
  "assessment": "One short sentence summarizing the recovery behavior."
}
```

Requirements:

- `scenario.setpoint_c`, `scenario.initial_temp_c`, `scenario.ambient_temp_c`, `scenario.process_gain_c_per_percent`, `scenario.time_constant_s`, `scenario.duration_s`, and `scenario.dt_s` must exactly match `incubator_case.json`.
- `controller.type` must be `PI`.
- `controller.Kp`, `controller.Ki`, `controller.Kd`, and `controller.lambda_s` must follow the rules above exactly.
- `closed_loop_trace` must cover at least `360s` and remain time-ordered.
- `closed_loop_trace` must be the simulator output for your reported `Kp` and `Ki`, with one entry per simulation step.
- The chamber must settle to within `+/-0.2C` of `37.0C` in at most `240s`.
- `steady_state_error_c` must be at most `0.15C` when averaged over the last `60s`.
- `peak_temperature_c` must stay below `37.5C`.
- `performance_summary` must be computed from the simulator trace with the provided metric helper.
- `controller.Kd` must be `0.0`.
- `assessment` must be a non-empty sentence.

No other output files are required.
