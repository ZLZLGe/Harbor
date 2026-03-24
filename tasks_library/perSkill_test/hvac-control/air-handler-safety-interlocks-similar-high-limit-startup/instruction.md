Use `air_handler_simulator.py` and `startup_profile.json` to run one air-handler startup sequence for a heating supply section.

Your target is to bring the measured supply temperature to `24.0C` and then keep it there for at least `120` seconds. The sequence must include:

1. A `trial_heat` phase that uses an initial heating command to move the discharge temperature upward.
2. A `closed_loop` phase that trims heater power and holds the target.

The critical rule is the high-limit protection:

- Before every heater command in both phases, check the current measured supply temperature against the `27.0C` high limit.
- If the current measured temperature is at or above `27.0C`, the applied heater command must be forced to `0.0` immediately.
- Keep a safety event log for every cutoff decision.
- Do not let the measured supply temperature exceed `27.0C` anywhere in the startup run.

The simulator only clamps heater power to the valid `0-100%` actuator range. The high-limit cutoff must be enforced by your own startup logic.

Write a single file named `startup_safety_report.json` with this structure:

```json
{
  "report_version": 1,
  "equipment_id": "AHU-7A",
  "target_temp_c": 24.0,
  "high_limit_c": 27.0,
  "hold_requirement_sec": 120.0,
  "phases": {
    "trial_heat": {
      "strategy": "fixed_boost_until_handoff",
      "data": [
        {
          "time_sec": 2.0,
          "pre_command_temp_c": 18.0,
          "measured_temp_c": 18.82,
          "raw_command_pct": 62.0,
          "applied_command_pct": 62.0,
          "high_limit_checked": true,
          "limit_triggered": false
        }
      ]
    },
    "closed_loop": {
      "strategy": "feedback_trim",
      "data": [
        {
          "time_sec": 24.0,
          "pre_command_temp_c": 23.82,
          "measured_temp_c": 23.86,
          "raw_command_pct": 39.5,
          "applied_command_pct": 39.5,
          "high_limit_checked": true,
          "limit_triggered": false
        }
      ]
    }
  },
  "safety_log": {
    "events": [
      {
        "phase": "interlock_audit",
        "time_sec": 0.0,
        "measured_temp_c": 27.2,
        "raw_command_pct": 45.0,
        "applied_command_pct": 0.0,
        "reason": "high_limit_cutoff"
      }
    ]
  },
  "interlock_audit": {
    "measured_temp_c": 27.2,
    "raw_command_pct": 45.0,
    "applied_command_pct": 0.0,
    "limit_triggered": true,
    "event_logged": true
  },
  "summary": {
    "target_reached": true,
    "hold_duration_sec": 120.0,
    "trial_duration_sec": 20.0,
    "closed_loop_duration_sec": 132.0,
    "startup_duration_sec": 152.0,
    "max_measured_temp_c": 24.1,
    "never_exceeded_high_limit": true
  },
  "safety_proof": {
    "high_limit_respected": true,
    "samples_checked": 76,
    "max_command_when_at_or_above_limit_pct": 0.0,
    "max_recorded_temp_c": 24.1
  }
}
```

Requirements for the report:

- Both phases must contain non-empty time-series data with monotonic timestamps.
- `high_limit_checked` must be `true` for every sample in both phases.
- `applied_command_pct` must stay within `0-100`.
- `summary.hold_duration_sec` must show at least `120` seconds at or above the target.
- `summary.max_measured_temp_c` and `safety_proof.max_recorded_temp_c` must agree with the logged data.
- Include the short `interlock_audit` record shown above: use a synthetic `27.2C` sensor reading and prove that your command logic cuts the heater command to `0.0` and records the event.
