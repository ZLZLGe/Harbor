Build a stop-and-go traffic jam assist simulation from `jam_vehicle.yaml` and `jam_radar_trace.csv`.

The assist should cruise at the capped speed when no target is visible, follow a lead vehicle through repeated slowdowns to full stops, hold cleanly at standstill, and restart smoothly when traffic moves again.

Use the provided radar trace as follows:
- `lead_speed` is the measured speed of the visible lead vehicle.
- `distance_hint` is only an initialization hint when a target first appears after blank rows. After that, keep simulating the gap yourself from relative motion until the target disappears.

Do not modify the input files.

Create these files:

1. `pid_controller.py`
Implement class `PIDController`.
- Constructor: `__init__(self, kp, ki, kd, output_limits=None, integral_limit=None)`
- Methods: `reset()`, `compute(error, dt)` returning a float

2. `jam_assist_system.py`
Implement class `TrafficJamAssist`.
- Constructor: `__init__(self, config)` where `config` is the parsed nested dict from `jam_vehicle.yaml`
- Method: `compute(ego_speed, lead_speed, gap_to_lead, dt)` returning `(acceleration_cmd, mode, gap_error, target_gap)`
- Modes:
  - `cruise` when no lead vehicle is visible
  - `follow` when tracking a moving or slowing target
  - `stop_hold` when the lead vehicle is stopped and the ego vehicle should remain settled
  - `emergency` when time-to-collision drops below the YAML threshold

3. `simulate_jam.py`
- Load tuned gains from `jam_tuning.yaml` at runtime. Do not hard-code tuned gains inside the simulator.
- Read `jam_vehicle.yaml` and `jam_radar_trace.csv`.
- Start from ego speed `0.0 m/s`.
- Respect acceleration limits `[-5.5, 2.8] m/s^2`.
- Respect the jerk comfort limit from the YAML file.
- Produce `jam_results.csv` with exactly these columns in this order:

```csv
time,ego_speed,lead_speed,gap_to_lead,acceleration_cmd,jerk,mode,gap_error,target_gap
```

- The CSV must have exactly 1801 rows covering `t=0.0` to `180.0` seconds at `0.1` second steps.

4. `jam_tuning.yaml`
Use this exact structure:

```yaml
pid_speed:
  kp: <value>
  ki: <value>
  kd: <value>
pid_gap:
  kp: <value>
  ki: <value>
  kd: <value>
```

Constraints for every gain:
- `kp` in `(0, 10)`
- `ki` in `[0, 5)`
- `kd` in `[0, 5)`
- The tuned values must differ from the initial gains in `jam_vehicle.yaml`

5. `jam_assist_report.md`
This is the primary output file.

Include sections covering:
- system design
- PID tuning methodology and final gains
- stop-and-go simulation results
- comfort and settling metrics

Targets to satisfy from the run outputs:
- Cruise near the capped speed of `22.0 m/s` on clear-lane segments
- Complete at least two full stop-and-go cycles from the provided radar trace
- Minimum simulated gap must stay above `6.0 m`
- Mean absolute gap error must stay below `1.5 m` in the settling windows `56-64 s`, `98-106 s`, and `136-146 s`
- The 95th percentile of `|jerk|` must stay below `2.5 m/s^3`
- After each full stop release, the ego vehicle should accelerate back above `5.0 m/s` within `5.0 s`

The task is complete only when `jam_results.csv`, `jam_tuning.yaml`, and `jam_assist_report.md` are all produced and consistent with the implementation.
