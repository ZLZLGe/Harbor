You need to produce exactly one file: `brine_mixer_control_summary.json`.

Use the provided mixing-process data in `brine_mixer_case.json` and validate your design with `brine_mixer_sim.py`. The outlet stream starts lean at `5.9%` salt while the recipe target is `6.8%`. A temporary fresh-water flush enters the vessel from `140s` to `220s`, so the controller must both finish the initial correction and recover after the flush.

Design a PI controller for this first-order concentration process, choose a closed-loop speed that stays smooth through the flush, then simulate the full batch and store the result in `brine_mixer_control_summary.json`.

Required JSON structure:

```json
{
  "scenario": {
    "target_concentration_pct": 6.8,
    "initial_concentration_pct": 5.9,
    "base_concentration_pct": 2.2,
    "nominal_brine_valve_pct": 46.0,
    "process_gain_pct_per_valve_pct": 0.1,
    "time_constant_s": 55.0,
    "duration_s": 420.0,
    "dt_s": 1.0
  },
  "mixing_event": {
    "flush_start_s": 140.0,
    "flush_end_s": 220.0,
    "dilution_shift_pct": 0.9
  },
  "controller": {
    "type": "PI",
    "Kp": 15.7143,
    "Ki": 0.2857,
    "Kd": 0.0,
    "lambda_s": 35.0,
    "bias_valve_pct": 46.0
  },
  "sampled_response": [
    {
      "time_s": 0.0,
      "concentration_pct": 5.9,
      "brine_valve_pct": 60.4,
      "dilution_active": false,
      "error_pct": 0.9
    }
  ],
  "phase_summary": {
    "startup_settling_time_s": 31.0,
    "flush_min_concentration_pct": 6.5801,
    "post_flush_recovery_time_s": 99.0,
    "steady_state_error_pct": 0.046,
    "integral_absolute_error_pct_s": 56.0563,
    "max_brine_valve_pct": 60.4,
    "final_concentration_pct": 6.8276
  },
  "blend_assessment": "One short sentence summarizing the concentration control behavior."
}
```

Requirements:

- `scenario` and `mixing_event` values must match `brine_mixer_case.json`.
- `sampled_response` must use exactly these times in order: `0, 40, 120, 160, 220, 280, 360, 420` seconds.
- `controller.Kd` must be `0.0`.
- `startup_settling_time_s` must be at most `95s` before the flush begins.
- `flush_min_concentration_pct` must stay at or above `6.57%` during the flush.
- `post_flush_recovery_time_s` must be at most `106s` measured from the end of the flush.
- `steady_state_error_pct` must be at most `0.053%` when averaged over the last `60s`.
- `integral_absolute_error_pct_s` must be at most `58.5`.
- `max_brine_valve_pct` must be at most `61.5%`.
- `blend_assessment` must be a non-empty sentence.

No other output files are required.
