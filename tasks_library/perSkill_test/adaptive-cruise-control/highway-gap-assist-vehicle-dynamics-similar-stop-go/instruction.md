Implement a highway stop-and-go gap assist simulation for a single ego vehicle. Create `/root/gap_assist.py`, read `/root/scenario_config.yaml` and `/root/lead_schedule.yaml`, simulate 180 seconds, and write `/root/stop_go_gap_results.csv`.

Requirements:

1. Build the simulation timeline from `t = 0.0` to `t = 180.0` seconds using the `dt` value from `scenario_config.yaml`. The expected timeline is inclusive of both endpoints.
2. Use the lead-vehicle schedule in `lead_schedule.yaml` to generate lead speed and visibility.
   - Each segment provides `start_s`, `end_s`, `visible`, `start_speed_mps`, and `end_speed_mps`.
   - For a row at time `t`, use the unique segment satisfying `start_s <= t < end_s`, except the last segment, which also includes `t = end_s`.
   - Inside a segment, linearly interpolate the lead speed between `start_speed_mps` and `end_speed_mps`.
   - `lead_position_m` at `t = 0` is `lead_vehicle.initial_position_m` from `scenario_config.yaml`.
   - For each step `k -> k+1`, update lead position with trapezoidal integration using the current and next lead speeds.
3. Simulate the ego vehicle with these exact rules.
   - Row `k` must store the ego state before integrating to the next time step.
   - `gap_m = lead_position_m - ego_position_m`
   - `safe_gap_m = min_gap_m + headway_s * ego_speed_mps`
   - `relative_speed = ego_speed_mps - lead_speed_mps`
   - `ttc_s = gap_m / relative_speed` when `relative_speed > 0`, otherwise `inf`
4. Use this mode state machine in order:
   - If `lead_visible == 0`, mode is `cruise`
   - Else if `gap_m <= emergency_factor * safe_gap_m` or `ttc_s < emergency_ttc_s`, mode is `emergency`
   - Else if `gap_m <= follow_factor * safe_gap_m`, mode is `follow`
   - Else mode is `cruise`
5. Use these exact control laws, then clamp acceleration to `[max_brake_mps2, max_accel_mps2]`.
   - `cruise`: `acceleration_cmd_mps2 = cruise_gain * (target_speed_mps - ego_speed_mps)`
   - `follow`: `acceleration_cmd_mps2 = follow_gap_gain * (gap_m - safe_gap_m) + follow_speed_gain * (lead_speed_mps - ego_speed_mps)`
   - `emergency`: `acceleration_cmd_mps2 = max_brake_mps2`
6. Update ego motion with constant-acceleration kinematics:
   - `ego_position_next = ego_position_m + ego_speed_mps * dt + 0.5 * acceleration_cmd_mps2 * dt^2`
   - `ego_speed_next = clamp(ego_speed_mps + acceleration_cmd_mps2 * dt, 0.0, max_speed_mps)`
7. Write `stop_go_gap_results.csv` with exactly these columns and this order:

```text
time,lead_visible,ego_position_m,ego_speed_mps,lead_position_m,lead_speed_mps,gap_m,safe_gap_m,ttc_s,mode,acceleration_cmd_mps2
```

8. `lead_visible` must be written as `0` or `1`. Keep numeric columns numeric. `ttc_s` may be `inf` when the relative speed is non-positive.
9. Do not modify the provided YAML input files.

No plots or extra reports are required.
