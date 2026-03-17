You are given four Adaptive Cruise Control calibration candidates in `acc_calibration_runs.csv` and the benchmark definition in `benchmark_spec.yaml`.

Create two output files in `/root`:

1. `calibration_metrics.csv`
2. `acc_calibration_benchmark.md`

Use these exact metric rules for each `calibration_id`:

- Cruise phase: rows with `0.0 <= time_s <= 30.0`, signal `ego_speed_mps`, target `30.0` m/s, settling band `+-2%`.
- Gap recovery phase: rows with `40.0 <= time_s <= 70.0`, signal `distance_m`, target `45.0` m, settling band `+-5%`.
- For the gap recovery phase, compute rise time and settling time with phase-local time (`time_s - 40.0`).
- Rise time: the first timestamp crossing 10% of target to the first timestamp crossing 90% of target.
- Overshoot: `max(signal)` above target as a percentage of target; if the signal never exceeds target, overshoot is `0.0`.
- Steady-state error: the absolute difference between target and the average of the final 10% of samples in that phase.
- Settling time: scan samples from the start of the phase; whenever the signal leaves the tolerance band, reset the candidate time. The reported settling time is the start of the final uninterrupted in-band interval.
- Minimum distance: the minimum non-empty `distance_m` value across the whole trace.

Benchmark gates:

- `cruise_rise_time_s <= 10.0`
- `cruise_overshoot_pct <= 3.0`
- `cruise_steady_state_error_mps <= 0.10`
- `cruise_settling_time_s <= 20.0`
- `recovery_rise_time_s <= 8.0`
- `recovery_overshoot_pct <= 5.0`
- `recovery_steady_state_error_m <= 0.10`
- `recovery_settling_time_s <= 12.0`
- `min_distance_m >= 26.0`

Overall score:

`overall_score = cruise_rise_time_s / 10.0 + cruise_overshoot_pct / 5.0 + cruise_steady_state_error_mps / 0.10 + cruise_settling_time_s / 20.0 + recovery_rise_time_s / 8.0 + recovery_overshoot_pct / 5.0 + recovery_steady_state_error_m / 0.10 + recovery_settling_time_s / 12.0`

Recommendation rule:

- Only candidates that pass every gate are eligible.
- Recommend the eligible calibration with the lowest `overall_score`.
- Compute `overall_score` from the unrounded metric values, then round the final score to 3 decimal places for output.

`calibration_metrics.csv` must contain exactly these columns in this order:

`calibration_id,cruise_rise_time_s,cruise_overshoot_pct,cruise_steady_state_error_mps,cruise_settling_time_s,recovery_rise_time_s,recovery_overshoot_pct,recovery_steady_state_error_m,recovery_settling_time_s,min_distance_m,passes_all_gates,overall_score,recommended`

Additional output requirements:

- Keep one row per calibration.
- Round every numeric metric and `overall_score` to 3 decimal places.
- Use lowercase string values `true` or `false` for `passes_all_gates` and `recommended`.
- Keep rows sorted by `calibration_id`.

`acc_calibration_benchmark.md` must:

- Start with the heading `# ACC Calibration Benchmark`.
- Include a `## Metric Method` section summarizing the metric definitions and benchmark gates.
- Include a `## Calibration Summary` section with a Markdown table that covers all columns from `calibration_metrics.csv`.
- Include a `## Recommended Calibration` section naming the chosen calibration and explaining briefly why it wins and why the rejected calibrations are not selected.
