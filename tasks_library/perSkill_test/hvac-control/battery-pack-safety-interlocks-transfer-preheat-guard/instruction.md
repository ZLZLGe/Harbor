Use `battery_pack_simulator.py` together with `preheat_profile.json` to run one cold-soak battery preheat sequence for pack `BP-17`.

The pack starts below its charge-ready module temperature. Your job is to warm it into the allowed charging window and produce a single safety report.

Charging window and protection rules:

- Module temperature must finish inside `17.0C` to `23.0C`.
- If any measured cell temperature reaches `32.0C` or higher, the applied heater command must be forced to `0.0%` immediately.
- After a cutoff, keep both `heater` and `charge_enable` off until every measured cell temperature falls below `30.5C`.
- `charge_enable` may only be `true` when the module temperature is inside the charging window and every measured cell temperature is below `30.5C`.

The simulator only evolves the thermal state and clamps heater commands to `0-100%`. The cutoff, latch, release, and charge permission logic must come from your own control procedure.

Write exactly one file named `battery_safety_report.json` with this structure:

```json
{
  "report_version": 1,
  "pack_id": "BP-17",
  "charge_window_c": {
    "min": 17.0,
    "max": 23.0
  },
  "cell_trip_temp_c": 32.0,
  "cell_reset_temp_c": 30.5,
  "trajectory": [
    {
      "time_sec": 0.0,
      "module_temp_c": 8.2,
      "cell_temps_c": [8.0, 8.4, 8.1, 8.3],
      "requested_heater_pct": 100.0,
      "applied_heater_pct": 100.0,
      "interlock_active": false,
      "charge_enable": false
    }
  ],
  "interlock_events": [
    {
      "time_sec": 75.0,
      "triggering_cell_index": 3,
      "trigger_cell_temp_c": 32.04,
      "requested_heater_pct": 100.0,
      "applied_heater_pct": 0.0,
      "charge_enable_after_cutoff": false,
      "reason": "cell_overtemp_cutoff"
    }
  ],
  "summary": {
    "trajectory_samples": 18,
    "interlock_trigger_times_sec": [75.0],
    "interlock_trigger_count": 1,
    "first_chargeable_time_sec": 85.0,
    "final_module_temp_c": 17.17,
    "final_max_cell_temp_c": 30.23,
    "final_charge_enable": true,
    "heater_forced_off_while_interlocked": true
  },
  "final_decision": {
    "charge_enable": true,
    "reason": "module_in_window_and_cells_below_reset",
    "module_temp_c": 17.17,
    "max_cell_temp_c": 30.23
  }
}
```

Requirements for the report:

- `trajectory` must be non-empty and use strictly increasing timestamps.
- Every `trajectory` sample must include the full measured cell temperature array.
- `applied_heater_pct` must stay within `0-100`.
- At least one cutoff event must occur and every cutoff must be listed in `interlock_events`.
- Whenever the measured maximum cell temperature is `>= 32.0C`, the applied heater must be `0.0` and `charge_enable` must be `false`.
- Once a cutoff happens, the heater must remain at `0.0` and `charge_enable` must remain `false` until all measured cell temperatures are below `30.5C`.
- `summary.first_chargeable_time_sec` must match the first trajectory sample where `charge_enable` becomes `true`.
- `final_decision` must agree with the last trajectory sample.
