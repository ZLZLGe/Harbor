You are given four industrial furnace control candidates in `furnace_temperature_runs.csv` and the acceptance criteria in `furnace_benchmark.yaml`.

Create two output files in `/root`:

1. `furnace_metrics.csv`
2. `furnace_temperature_report.md`

Use these exact metric rules for each `configuration_id`:

- Heat-up phase: rows with `0.0 <= time_min <= 80.0`, signal `temperature_c`, target `850.0` C, settling band `+-1.5%`.
- Disturbance-recovery phase: rows with `90.0 <= time_min <= 140.0`.
- For disturbance recovery, first compute `recovery_floor_c` as the minimum `temperature_c` inside the recovery phase.
- Define the transformed recovery signal as `recovery_progress_c = temperature_c - recovery_floor_c`.
- Define the recovery target as `recovery_target_c = 850.0 - recovery_floor_c`.
- For the recovery phase, compute rise time and settling time with phase-local time (`time_min - 90.0`).
- Rise time: the first timestamp crossing 10% of target to the first timestamp crossing 90% of target.
- Overshoot: `max(signal)` above target as a percentage of target; if the signal never exceeds target, overshoot is `0.0`.
- Steady-state error: the absolute difference between target and the average of the final 10% of samples in that phase.
- Settling time: scan samples from the start of the phase; whenever the signal leaves the tolerance band, reset the candidate time. The reported settling time is the start of the final uninterrupted in-band interval.

Acceptance gates:

- `heatup_rise_time_min <= 32.0`
- `heatup_overshoot_pct <= 1.0`
- `heatup_steady_state_error_c <= 3.0`
- `heatup_settling_time_min <= 50.0`
- `recovery_floor_c >= 735.0`
- `recovery_rise_time_min <= 14.0`
- `recovery_overshoot_pct <= 1.0`
- `recovery_steady_state_error_c <= 0.1`
- `recovery_settling_time_min <= 20.0`

Overall score:

`overall_score = heatup_rise_time_min / 32.0 + heatup_overshoot_pct / 1.0 + heatup_steady_state_error_c / 3.0 + heatup_settling_time_min / 50.0 + recovery_rise_time_min / 14.0 + recovery_overshoot_pct / 1.0 + recovery_steady_state_error_c / 0.1 + recovery_settling_time_min / 20.0`

Recommendation rule:

- Only configurations that pass every gate are eligible.
- Recommend the eligible configuration with the lowest `overall_score`.
- Compute `overall_score` from the unrounded metric values, then round the final score to 3 decimal places for output.

`furnace_metrics.csv` must contain exactly these columns in this order:

`configuration_id,heatup_rise_time_min,heatup_overshoot_pct,heatup_steady_state_error_c,heatup_settling_time_min,recovery_floor_c,recovery_rise_time_min,recovery_overshoot_pct,recovery_steady_state_error_c,recovery_settling_time_min,passes_all_gates,overall_score,recommended`

Additional output requirements:

- Keep one row per configuration.
- Round every numeric metric and `overall_score` to 3 decimal places.
- Use lowercase string values `true` or `false` for `passes_all_gates` and `recommended`.
- Keep rows sorted by `configuration_id`.

`furnace_temperature_report.md` must:

- Start with the heading `# Industrial Furnace Temperature Report`.
- Include a `## Metric Method` section summarizing the metric definitions and acceptance gates.
- Include a `## Configuration Summary` section with a Markdown table that covers all columns from `furnace_metrics.csv`.
- Include a `## Recommended Configuration` section naming the chosen configuration and explaining briefly why it wins and why the rejected configurations are not selected.
