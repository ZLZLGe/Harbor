You are given three quadcopter altitude-hold traces in `quadcopter_altitude_runs.csv` and the scorecard definition in `scorecard_spec.yaml`.

Create exactly one output file in `/root`:

`quadcopter_altitude_scorecard.json`

For each `controller_id`, compute these metrics and compare the controllers:

- Climb step phase: rows with `0.0 <= time_s <= 18.0`, signal `altitude_m`, target `12.0` m, settling band `+-2%` of target.
- Gust recovery phase: rows with `20.0 <= time_s <= 36.0`.
- For gust recovery, define `recovery_origin_m` as the first `altitude_m` sample in that phase for the controller.
- For gust recovery, define `recovery_signal_m = altitude_m - recovery_origin_m`.
- For gust recovery, define `recovery_target_m = 12.0 - recovery_origin_m`.
- For gust recovery, compute rise time and settling time with phase-local time (`time_s - 20.0`) and use a settling band of `+-2%` of `recovery_target_m`.
- Rise time: the first timestamp crossing `10%` of the target to the first timestamp crossing `90%` of the target.
- Overshoot: `max(signal)` above target as a percentage of target; if the signal never exceeds target, overshoot is `0.0`.
- Steady-state error: the absolute difference between target and the average of the final `20%` of samples in that phase.
- Settling time: scan samples from the start of the phase; whenever the signal leaves the tolerance band, reset the candidate time. The reported settling time is the start of the final uninterrupted in-band interval.

Limits:

- `climb_rise_time_s <= 8.0`
- `climb_overshoot_pct <= 2.0`
- `climb_settling_time_s <= 15.0`
- `climb_steady_state_error_m <= 0.15`
- `recovery_rise_time_s <= 6.0`
- `recovery_overshoot_pct <= 2.0`
- `recovery_settling_time_s <= 12.0`
- `recovery_steady_state_error_m <= 0.05`

Overall score:

`overall_score = climb_rise_time_s / 8.0 + climb_overshoot_pct / 2.0 + climb_settling_time_s / 15.0 + climb_steady_state_error_m / 0.15 + recovery_rise_time_s / 6.0 + recovery_overshoot_pct / 2.0 + recovery_settling_time_s / 12.0 + recovery_steady_state_error_m / 0.05`

Pass and ranking rules:

- `passes_all_limits` is `true` only if all eight limits are satisfied.
- Rank all passing controllers first by ascending `overall_score`.
- After that, rank failing controllers by ascending `overall_score`.
- `best_controller_id` must match the controller with `rank = 1`.

Output JSON requirements:

- The top-level object must contain exactly these keys: `best_controller_id`, `controllers`, `recommendation_summary`.
- `controllers` must be an array sorted by `rank` ascending.
- Each controller object must contain exactly these keys: `controller_id`, `rank`, `passes_all_limits`, `overall_score`, `climb_step`, `gust_recovery`.
- `climb_step` and `gust_recovery` must each contain exactly these keys: `rise_time_s`, `overshoot_pct`, `settling_time_s`, `steady_state_error_m`.
- Round every numeric metric and `overall_score` to 3 decimal places.
- Use JSON booleans for `passes_all_limits`.
- `recommendation_summary` must mention all three controller IDs and explain briefly why the selected controller wins.
