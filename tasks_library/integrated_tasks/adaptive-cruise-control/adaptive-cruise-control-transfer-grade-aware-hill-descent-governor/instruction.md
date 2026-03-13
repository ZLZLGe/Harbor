Build a grade-aware hill descent governor for a loaded vehicle using these inputs:

- `descent_vehicle.yaml`
- `grade_profile.csv`
- `target_speed_profile.csv`

Do not modify the input files.

Create these files:

1. `pid_controller.py`
Implement class `PIDController`.
- Constructor: `__init__(self, kp, ki, kd, output_limits=None, integral_limit=None)`
- Methods: `reset()` and `compute(error, dt)` returning a float

2. `hill_descent_governor.py`
Implement class `HillDescentGovernor`.
- Constructor: `__init__(self, config)` where `config` is the parsed nested dict from `descent_vehicle.yaml`
- Method: `compute(vehicle_speed, target_speed, grade_percent, dt)` returning `(brake_command, brake_decel, speed_error)`
- The controller must be grade-aware: use the current slope together with tuned PID feedback so braking authority scales appropriately on steeper downhill sections.

3. `descent_simulation.py`
- Load tuned gains from `descent_tuning.yaml` at runtime. Do not hard-code the tuned gains inside the simulator.
- Read both CSV profiles and align them by `time`.
- Start from the initial speed in the YAML file.
- Simulate the longitudinal downhill dynamics for the full profile while respecting the service brake limit from the YAML file.
- Produce `descent_simulation_results.csv` with exactly these columns in this order:

```csv
time,grade_percent,target_speed,vehicle_speed,speed_error,brake_command,brake_decel,gravity_accel,drag_accel,rolling_accel,net_accel
```

- The CSV must have exactly 361 rows covering `t=0.0` to `180.0` seconds at `0.5` second steps.

4. `descent_tuning.yaml`
Use this exact structure:

```yaml
pid_brake:
  kp: <value>
  ki: <value>
  kd: <value>
```

Constraints:
- `kp` in `(0, 10)`
- `ki` in `[0, 5)`
- `kd` in `[0, 5)`
- The tuned values must differ from the initial gains in `descent_vehicle.yaml`

5. `descent_metrics.yaml`
Use this exact structure:

```yaml
max_transient_overspeed_mps: <float>
steady_max_overspeed_mps: <float>
steady_mean_abs_error_mps: <float>
settling_times_s:
  after_target_drop_45s: <float>
  after_grade_step_75s: <float>
  after_target_drop_100s: <float>
  after_target_change_150s: <float>
safety:
  max_vehicle_speed_mps: <float>
  max_brake_decel_mps2: <float>
  within_service_brake_limit: <bool>
```

Compute the steady-state metrics over these windows only:
- `0.0-37.0 s`
- `53.0-67.0 s`
- `83.0-92.0 s`
- `108.0-142.0 s`
- `158.0-180.0 s`

Define each settling time as the first time after the profile change when `|speed_error| <= 0.35 m/s` for 6 consecutive samples.

Targets to satisfy from the run outputs:
- `max_transient_overspeed_mps < 2.2`
- `steady_max_overspeed_mps < 0.5`
- `steady_mean_abs_error_mps < 0.15`
- `settling_times_s.after_target_drop_45s < 4.0`
- `settling_times_s.after_grade_step_75s < 2.0`
- `settling_times_s.after_target_drop_100s < 4.0`
- `settling_times_s.after_target_change_150s < 4.0`
- Mean `brake_command` over `110.0-145.0 s` must stay above `0.08`
- `safety.max_vehicle_speed_mps <= 24.5`
- `safety.within_service_brake_limit` must be `true`

The task is complete only when `descent_simulation_results.csv`, `descent_tuning.yaml`, and `descent_metrics.yaml` are all produced and consistent with the implementation.
