You need to produce exactly one file: `tank_level_controller_report.json`.

Use the provided liquid-level process data in `tank_level_case.json` and validate your design with `tank_level_sim.py`. The storage tank starts at `50.0%` level while a constant downstream draw is already active. Your target is to bring the level to `64.0%` and hold it there.

Design a PI controller for this first-order level process, choose a closed-loop speed that recovers smoothly under the constant outflow, then simulate the full response and store the report in `tank_level_controller_report.json`.

Required JSON structure:

```json
{
  "scenario": {
    "target_level_pct": 64.0,
    "initial_level_pct": 50.0,
    "base_level_pct": 38.0,
    "constant_outflow_equivalent_pct": 6.0,
    "process_gain_pct_per_valve_pct": 0.72,
    "time_constant_s": 95.0,
    "duration_s": 720.0,
    "dt_s": 2.0
  },
  "controller": {
    "type": "PI",
    "Kp": 3.08642,
    "Ki": 0.032489,
    "Kd": 0.0,
    "lambda_s": 42.75
  },
  "checkpoints": [
    {
      "time_s": 60.0,
      "level_pct": 56.39,
      "valve_open_pct": 44.14,
      "error_pct": 7.61
    }
  ],
  "performance_summary": {
    "settling_time_s": 254.0,
    "steady_state_error_pct": 0.02,
    "peak_level_pct": 63.99,
    "minimum_level_pct": 50.28,
    "final_level_pct": 63.99
  },
  "balance_analysis": {
    "required_hold_valve_pct": 44.44,
    "average_valve_pct_last_120s": 44.44,
    "outflow_rejection_ok": true
  },
  "assessment": "One short sentence summarizing the liquid-level recovery."
}
```

Requirements:

- `checkpoints` must include exactly these times in order: `60, 120, 240, 360, 540, 720` seconds.
- The reported scenario values must match `tank_level_case.json`.
- `controller.Kd` must be `0.0`.
- The liquid level must settle to within `+/-1.0%` of `64.0%` in at most `320s`.
- `steady_state_error_pct` must be at most `0.25%` when averaged over the last `120s`.
- `peak_level_pct` must stay below `64.5%`.
- `minimum_level_pct` must stay above `49.5%`.
- `average_valve_pct_last_120s` must be within `1.0` percentage point of `required_hold_valve_pct`.
- `outflow_rejection_ok` must truthfully summarize whether the controller both meets the settling target and balances the constant outflow.
- `assessment` must be a non-empty sentence.

No other output files are required.
