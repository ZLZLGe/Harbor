Use `tank_fill_simulator.py` together with `fill_recipe.json` to run one safe fill procedure for storage tank `TK-204`.

The work has two required simulator phases:

1. `pulse_test`: reset the simulator into the pulse-test scenario from the recipe and apply the fixed requested inlet profile from the recipe.
2. `auto_fill`: reset the simulator into the auto-fill scenario, raise the measured level into the target band, and keep it there.

Operating targets:

- Target band: `84.0%` to `88.0%`
- High-level interlock: `92.0%`
- Reopen threshold after a cutoff: measured level must fall below `89.5%`
- Hold requirement in the target band during `auto_fill`: at least `120` continuous seconds

Critical rule for both phases:

- Before every inlet-valve command, check the current measured level.
- If the measured level is at or above `92.0%`, the applied inlet command must be forced to `0.0%` immediately.
- Once a cutoff happens, keep fill actions frozen until the measured level falls below `89.5%`.
- Record every interlock activation in a safety event log.
- Do not let the measured level reach `100.0%`.

The simulator only applies the hydraulic response and clamps the actuator to `0-100%`. The high-level cutoff and freeze logic must come from your own procedure.

Write exactly one output file named `fill_interlock_summary.json` with this structure:

```json
{
  "report_version": 1,
  "tank_id": "TK-204",
  "target_band_pct": {
    "low": 84.0,
    "high": 88.0
  },
  "high_level_interlock_pct": 92.0,
  "reopen_fill_pct": 89.5,
  "phases": {
    "pulse_test": {
      "requested_profile_pct": [80.0, 80.0, 80.0, 80.0, 40.0, 40.0, 0.0, 0.0],
      "data": [
        {
          "time_sec": 2.0,
          "pre_command_level_pct": 91.55,
          "measured_level_pct": 91.79,
          "requested_inlet_pct": 80.0,
          "applied_inlet_pct": 80.0,
          "high_level_checked": true,
          "interlock_active": false,
          "fill_frozen": false
        }
      ]
    },
    "auto_fill": {
      "strategy": "band_fill_with_reopen_hysteresis",
      "data": [
        {
          "time_sec": 2.0,
          "pre_command_level_pct": 76.0,
          "measured_level_pct": 76.67,
          "requested_inlet_pct": 100.0,
          "applied_inlet_pct": 100.0,
          "high_level_checked": true,
          "interlock_active": false,
          "fill_frozen": false
        }
      ]
    }
  },
  "safety_log": {
    "events": [
      {
        "phase": "pulse_test",
        "time_sec": 4.0,
        "measured_level_pct": 92.03,
        "requested_inlet_pct": 80.0,
        "applied_inlet_pct": 0.0,
        "reason": "high_level_cutoff"
      }
    ]
  },
  "summary": {
    "target_band_reached": true,
    "contiguous_hold_sec": 120.0,
    "final_level_pct": 85.6,
    "max_level_pct": 92.03,
    "interlock_event_count": 1,
    "never_overflowed": true
  },
  "safety_proof": {
    "all_samples_checked": true,
    "samples_at_or_above_interlock": 1,
    "max_applied_inlet_at_or_above_interlock_pct": 0.0,
    "freeze_respected_until_reopen": true,
    "overflow_margin_pct": 7.97
  }
}
```

Requirements for the summary:

- Both phases must contain non-empty time-series data with strictly increasing timestamps.
- `high_level_checked` must be `true` for every sample in both phases.
- `applied_inlet_pct` must stay within `0-100`.
- `summary.contiguous_hold_sec` must show at least `120` continuous seconds inside the target band during `auto_fill`.
- `summary.max_level_pct` must match the maximum measured level found in the phase logs.
- `safety_log.events` must contain every interlock activation and each logged activation must show `applied_inlet_pct = 0.0`.
- `safety_proof.max_applied_inlet_at_or_above_interlock_pct` must prove that no fill command was applied when the measured level was at or above `92.0%`.
