You need to implement a drone altitude-hold simulation that follows the target altitude profile in `telemetry.csv` using configuration from the nested `flight_params.yaml`. The drone starts in a low hover, climbs to a 12 m hold, rejects gust disturbances, then descends and stabilizes at 8 m. Targets: climb rise time <8 s for the 12 m step, climb overshoot <0.8 m, mean absolute altitude error <0.45 m during the 18-30 s gust-hold window, mean absolute altitude error <0.35 m during the 40-48 s descent-settle window. Also respect the constraints: total duration 48 s, timestep 0.2 s, thrust limits [0.0, 26.0] N, nominal hover thrust 17.7 N, vertical acceleration limit +/-4.0 m/s^2, altitude never below 0 m.

Data is available in `flight_params.yaml` (drone specs, mission settings, and nested controller defaults) and `telemetry.csv` (241 rows for t=0-48 s with columns: `time`, `target_altitude`, `wind_accel`, `phase`).

First, create `altitude_controller.py` to implement the PID controller. Then, create `altitude_hold.py` to implement the altitude-hold logic and `run_flight.py` to run the vertical simulation. Next, tune the altitude-loop gains, saving the result in `altitude_tuning.yaml`. Finally, run the full flight simulation, producing `flight_results.csv` and `altitude_report.md`.

Examples output format:

`altitude_controller.py`:
Class: `PIDController`
Constructor: `__init__(self, kp, ki, kd)`
Methods: `reset()`, `compute(error, dt)` returns float

`altitude_hold.py`:
Class: `AltitudeHoldController`
Constructor: `__init__(self, config)` where `config` is the nested dict loaded from `flight_params.yaml`
Method: `compute(target_altitude, altitude, vertical_speed, dt)` returns tuple `(thrust_cmd, altitude_error)`

`run_flight.py`:
Read tuned gains from `altitude_tuning.yaml` at runtime.
Do not embed auto-tuning logic because gains should be loaded from the yaml file.
Use `telemetry.csv` for the target profile and wind disturbance.

`altitude_tuning.yaml`, with `kp` in `(0, 6)`, `ki` in `[0, 2)`, `kd` in `[0, 3)`, and `damping_gain` in `(0, 2]`:
```yaml
altitude_loop:
  kp: <value>
  ki: <value>
  kd: <value>
  damping_gain: <value>
```

`flight_results.csv`:
(exactly 241 rows, exact same column order)
```csv
time,target_altitude,altitude,vertical_speed,thrust_cmd,error,phase
0.0,1.5,1.5,0.0,17.7,0.0,precheck
0.2,1.5,1.5,0.0,17.7,0.0,precheck
0.4,1.5,1.5,0.0,17.7,0.0,precheck
```

`altitude_report.md`:
Include sections covering:
- System design
- Gain tuning methodology and final gains
- Flight results and performance metrics
