You are given three robotic joint servo traces in `robotic_joint_runs.csv` and the validation rules in `validation_spec.yaml`.

Create exactly one output file in `/root`:

`robotic_joint_validation.yaml`

For each `controller_id`, compute these metrics:

- Step response phase: rows with `0.0 <= time_s <= 11.0`, signal `joint_angle_deg`, target `60.0` deg, settling band `+-2%` of target.
- Load-switch recovery phase: rows with `12.0 <= time_s <= 22.0`.
- For load-switch recovery, define `recovery_origin_deg` as the first `joint_angle_deg` sample in that phase for the controller.
- For load-switch recovery, define `recovery_signal_deg = joint_angle_deg - recovery_origin_deg`.
- For load-switch recovery, define `recovery_target_deg = 60.0 - recovery_origin_deg`.
- For load-switch recovery, compute rise time and settling time with phase-local time (`time_s - 12.0`) and use a settling band of `+-2%` of `recovery_target_deg`.
- Rise time: the first timestamp crossing `10%` of the target to the first timestamp crossing `90%` of the target.
- Overshoot: `max(signal)` above target as a percentage of target; if the signal never exceeds target, overshoot is `0.0`.
- Steady-state error: the absolute difference between target and the average of the final `20%` of samples in that phase.
- Settling time: scan samples from the start of the phase; whenever the signal leaves the tolerance band, reset the candidate time. The reported settling time is the start of the final uninterrupted in-band interval.

Acceptance gates:

- `step_rise_time_s <= 4.0`
- `step_overshoot_pct <= 5.0`
- `step_settling_time_s <= 6.0`
- `step_steady_state_error_deg <= 0.5`
- `load_rise_time_s <= 3.0`
- `load_overshoot_pct <= 5.0`
- `load_settling_time_s <= 5.0`
- `load_steady_state_error_deg <= 0.3`

Overall score:

`overall_score = step_rise_time_s / 4.0 + step_overshoot_pct / 5.0 + step_settling_time_s / 6.0 + step_steady_state_error_deg / 0.5 + load_rise_time_s / 3.0 + load_overshoot_pct / 5.0 + load_settling_time_s / 5.0 + load_steady_state_error_deg / 0.3`

Ranking and recommendation rules:

- Controllers that pass every gate rank ahead of controllers that fail one or more gates.
- Within each group, rank by ascending `overall_score`.
- `recommended_controller_id` must match the controller with `rank = 1`.

Output YAML requirements:

- The top-level mapping must contain exactly these keys: `recommended_controller_id`, `controllers`, `acceptance_summary`.
- `controllers` must be a list sorted by `rank` ascending.
- Each controller entry must contain exactly these keys: `controller_id`, `rank`, `passes_acceptance`, `overall_score`, `step_response`, `load_recovery`.
- `step_response` and `load_recovery` must each contain exactly these keys: `rise_time_s`, `overshoot_pct`, `settling_time_s`, `steady_state_error_deg`.
- `acceptance_summary` must contain exactly these keys: `accepted_controllers`, `rejected_controllers`, `conclusion`.
- Round every numeric metric and `overall_score` to 3 decimal places.
- Use YAML booleans for `passes_acceptance`.
- `accepted_controllers` and `rejected_controllers` must list controller IDs in the same order as the ranked `controllers` array.
- `conclusion` must mention all three controller IDs and explain briefly why the recommended controller wins and why the rejected controllers do not pass.
