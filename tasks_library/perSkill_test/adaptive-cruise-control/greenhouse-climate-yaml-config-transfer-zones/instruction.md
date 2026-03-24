Implement a greenhouse climate replay for multiple growing zones. The system must load all zone targets, actuator limits, simulation coefficients, and fallback rules from the provided YAML file, then replay the provided CSV sensor trace and produce a YAML strategy summary plus simulation artifacts.

Create these files:

`zone_controller.py`
- Define class `ZoneClimateController`.
- Constructor: `__init__(self, zone_name, zone_policy, global_config)`.
- Methods:
  - `reset()`
  - `compute_controls(estimated_temp_c, estimated_humidity_pct, outside_temp_c, outside_humidity_pct, solar_wm2, fallback_active)` returning a dict with numeric keys `heater_kw`, `vent_pct`, and `mister_lpm`.
- Respect the per-zone actuator limits from `greenhouse_policies.yaml`.

`greenhouse_replay.py`
- Load `greenhouse_policies.yaml` and `sensor_trace.csv` at runtime.
- Do not hard-code the zone list, targets, limits, fallback settings, or model coefficients.
- Replay every row in `sensor_trace.csv` in timestamp order for each zone.
- Blank `temp_sensor_c` / `humidity_sensor_pct` cells must trigger the fallback behavior described by the YAML config.
- Write these outputs:
  - `greenhouse_strategy.yaml`
  - `climate_simulation.csv`
  - `greenhouse_report.md`

Input files:
- `greenhouse_policies.yaml`
- `sensor_trace.csv`

`greenhouse_policies.yaml` contains nested sections for:
- replay settings
- climate model coefficients
- global fallback rules
- per-zone targets, actuator limits, initial state, and safe fallback outputs

`sensor_trace.csv` columns:
- `time_min`
- `zone`
- `outside_temp_c`
- `outside_humidity_pct`
- `solar_wm2`
- `temp_sensor_c`
- `humidity_sensor_pct`

Replay requirements:
- Duration: 120 minutes
- Time step: 10 minutes
- Simulate every zone defined in `greenhouse_policies.yaml`
- Use the initial state from YAML for each zone
- Keep temperature and humidity inside the YAML target bands as much as possible during the replay
- Each zone must finish with:
  - temperature in-band ratio at least `0.75`
  - humidity in-band ratio at least `0.90`
- Each zone has at least one fallback event during the replay

`greenhouse_strategy.yaml` must use this nested structure:

```yaml
replay:
  rows_processed: <int>
  time_step_minutes: <int>
zones:
  <zone_name>:
    crop: <string>
    target_band:
      temperature_c:
        min: <float>
        max: <float>
      humidity_pct:
        min: <float>
        max: <float>
    actuator_limits:
      heater_kw_max: <float>
      vent_pct_max: <float>
      mister_lpm_max: <float>
    fallback_mode:
      missing_sensor_policy: "hold-last-then-estimate"
      max_missing_steps: <int>
    derived_strategy:
      temperature_gain_kw_per_c: <float>
      vent_gain_pct_per_c: <float>
      mister_gain_lpm_per_pct: <float>
    metrics:
      temperature_in_band_ratio: <float>
      humidity_in_band_ratio: <float>
      fallback_events: <int>
      max_temperature_deviation_c: <float>
      max_humidity_deviation_pct: <float>
      final_estimated_temperature_c: <float>
      final_estimated_humidity_pct: <float>
overall:
  zones_simulated: <int>
  all_temperature_ratios_ok: <bool>
  all_humidity_ratios_ok: <bool>
  all_constraints_ok: <bool>
```

`climate_simulation.csv` requirements:
- Exactly the same number of rows as `sensor_trace.csv`
- Exact column order:

```csv
time_min,zone,estimated_temp_c,estimated_humidity_pct,heater_kw,vent_pct,mister_lpm,temp_in_band,humidity_in_band,fallback_applied
```

`greenhouse_report.md` must include short sections covering:
- system design
- fallback handling
- replay results

Do not modify the provided input files.
