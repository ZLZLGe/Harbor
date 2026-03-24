Implement `/root/zone_speed_profile.py`. Read `/root/route_profile.yaml` and `/root/zone_map.tsv`, simulate the full delivery route, and write `/root/zone_speed_profile_metrics.yaml`.

Use these exact rules:

1. `route_profile.yaml` provides:
   - `scenario.id`
   - `scenario.dt_s`
   - `scenario.initial_position_m`
   - `scenario.initial_speed_mps`
   - `vehicle.max_accel_mps2`
   - `vehicle.max_brake_mps2`
   - `vehicle.max_speed_mps`
   - `vehicle.rolling_drag_mps2`
   - `vehicle.quadratic_drag_coeff`
   - `controller.accel_gain`
   - `controller.brake_gain`
   - `controller.brake_margin_m`
   - `controller.cruise_tolerance_mps`
   - `assessment.stop_error_tolerance_m`
2. `zone_map.tsv` is a tab-separated file with exactly these columns:
   - `zone_id`
   - `start_m`
   - `end_m`
   - `speed_limit_mps`
   - `stop_id`
   - `stop_position_m`
   Blank `stop_id` and `stop_position_m` mean that zone has no docking stop.
3. Start at `t = 0.0` with the initial position and speed from `route_profile.yaml`. Each simulation row represents the robot state before integrating the next step. The active zone is the unique row satisfying `start_m <= position_m < end_m`, except the last zone, which also includes `position_m = end_m`.
4. For each row, build constraint candidates in this order:
   - If the active zone has an unserved stop and its `stop_position_m <= position_m`, include that stop with `constraint_speed_mps = 0.0`.
   - For every unserved future stop with `stop_position_m > position_m`, include that stop with `constraint_speed_mps = 0.0`.
   - For every future zone boundary where the next zone has a strictly lower `speed_limit_mps` than the active zone, include the next zone start position with `constraint_speed_mps = next_zone.speed_limit_mps`.
   - Choose the candidate with the smallest position. If no candidate exists, there is no active constraint.
5. When a constraint exists, compute:
   - `constraint_distance_m = max(constraint_position_m - position_m, 0.0)`
   - `braking_distance_m = max((speed_mps^2 - constraint_speed_mps^2) / (2 * abs(max_brake_mps2)), 0.0)`
   If no constraint exists, set `braking_distance_m = 0.0`.
6. Determine the mode using exactly this priority:
   - `brake` if a constraint exists, `constraint_distance_m <= braking_distance_m + brake_margin_m`, and `speed_mps > constraint_speed_mps + 0.05`
   - `accelerate` if not braking and `speed_mps < active_speed_limit_mps - cruise_tolerance_mps`
   - otherwise `coast`
7. Compute the commanded acceleration:
   - `accelerate`: `command_accel_mps2 = min(max_accel_mps2, accel_gain * (active_speed_limit_mps - speed_mps))`
   - `coast`: `command_accel_mps2 = 0.0`
   - `brake`: `command_accel_mps2 = max(max_brake_mps2, -brake_gain * (speed_mps - constraint_speed_mps))`
8. Compute net acceleration and integrate with constant-acceleration kinematics:
   - `net_accel_mps2 = command_accel_mps2 - rolling_drag_mps2 - quadratic_drag_coeff * speed_mps^2`
   - `raw_speed_next_mps = clamp(speed_mps + net_accel_mps2 * dt_s, 0.0, max_speed_mps)`
   - `raw_position_next_m = position_m + speed_mps * dt_s + 0.5 * net_accel_mps2 * dt_s^2`
9. Apply stop capture after the raw integration step:
   - Find the earliest unserved stop satisfying `position_m <= stop_position_m <= raw_position_next_m`.
   - If such a stop exists, record one stop capture at `t + dt_s` with:
     - `stop_id`
     - `target_position_m`
     - `captured_time_s`
     - `position_error_m = abs(raw_position_next_m - stop_position_m)`
     - `speed_error_mps = raw_speed_next_mps`
   - Then snap the next state to the stop target exactly:
     - `position_next_m = stop_position_m`
     - `speed_next_mps = 0.0`
   - Mark that stop as served.
   - If multiple stops would be crossed in one step, only use the earliest one.
10. If no stop is captured in that step, carry forward:
   - `position_next_m = raw_position_next_m`
   - `speed_next_mps = raw_speed_next_mps`
11. Continue until the final stop in the last zone is captured.
12. Write `/root/zone_speed_profile_metrics.yaml` with exactly this top-level structure:

```yaml
scenario_id: <string>
time_step_s: <number>
samples: <integer>
mode_durations_s:
  accelerate: <number>
  coast: <number>
  brake: <number>
zone_metrics:
  - zone_id: <string>
    entry_time_s: <number>
    exit_time_s: <number>
    sample_count: <integer>
    mean_speed_mps: <number>
    peak_speed_mps: <number>
    speed_limit_mps: <number>
stop_metrics:
  - stop_id: <string>
    target_position_m: <number>
    captured_time_s: <number>
    position_error_m: <number>
    speed_error_mps: <number>
summary:
  completed_stops: <integer>
  final_time_s: <number>
  total_distance_m: <number>
  max_speed_mps: <number>
  max_limit_excess_mps: <number>
  all_stops_within_tolerance: <boolean>
  max_stop_error_m: <number>
```

13. Build `mode_durations_s` from the number of executed integration steps in each mode multiplied by `dt_s`.
14. Build `zone_metrics` in the same order as `zone_map.tsv`, using all simulation rows whose active zone matches that zone:
   - `entry_time_s` is the first row time in the zone.
   - `exit_time_s` is the last row time in the zone.
   - `sample_count` is the number of rows in the zone.
   - `mean_speed_mps` and `peak_speed_mps` come from the stored pre-integration speeds in that zone.
15. `summary.max_limit_excess_mps` is the maximum of `max(speed_mps - active_speed_limit_mps, 0.0)` over all stored simulation rows.
16. `summary.all_stops_within_tolerance` is true only when every recorded `position_error_m` is less than or equal to `assessment.stop_error_tolerance_m`.
17. Round every numeric value written to YAML to 6 decimal places. Keep integers as integers and booleans as YAML booleans.
18. Do not modify the provided YAML or TSV input files.

No plots or extra output files are required.
