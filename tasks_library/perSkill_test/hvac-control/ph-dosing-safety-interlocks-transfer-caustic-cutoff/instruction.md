Use `ph_dosing_simulator.py` together with `dosing_profile.json` to run one caustic-dosing audit for fermentor `FERM-22`.

This task has two required simulator phases:

1. `trial_dose`: reset the simulator into the `trial_dose` scenario and apply the fixed requested caustic profile from the recipe.
2. `regulate`: reset the simulator into the `regulate` scenario and drive the measured pH toward `6.8`.

Operating targets and safety rules:

- Target pH: `6.8`
- Acceptable final target band: `6.75` to `6.90`
- High-pH cutoff: `7.2`
- Valid caustic-pump command range: `0.0%` to `45.0%`

Before every pump command in both phases:

- Check the current measured pH first.
- If the measured pH is at or above `7.2`, the applied caustic command must be forced to `0.0%` immediately and logged as a cutoff event.
- Otherwise clamp the command into the valid `0.0-45.0%` range. If clamping changes the requested command, log a clamp event.

The simulator only updates the pH state from the applied command. The cutoff, output clamp, and event logging logic must come from your own procedure.

Write exactly one file named `dosing_interlock_audit.json` with this structure:

```json
{
  "report_version": 1,
  "fermentor_id": "FERM-22",
  "target_ph": 6.8,
  "target_band": {
    "low": 6.75,
    "high": 6.9
  },
  "high_limit_ph": 7.2,
  "pump_limits_pct": {
    "min": 0.0,
    "max": 45.0
  },
  "phases": {
    "trial_dose": {
      "requested_profile_pct": [45.0, 45.0, 35.0, 35.0, 20.0, 0.0],
      "data": [
        {
          "time_sec": 10.0,
          "pre_command_ph": 7.05,
          "measured_ph": 7.123,
          "raw_caustic_pct": 45.0,
          "applied_caustic_pct": 45.0,
          "safety_checked": true,
          "high_limit_triggered": false,
          "command_clamped": false
        }
      ]
    },
    "regulate": {
      "strategy": "proportional_trim",
      "tail_window_samples": 6,
      "data": [
        {
          "time_sec": 10.0,
          "pre_command_ph": 6.12,
          "measured_ph": 6.2674,
          "raw_caustic_pct": 61.6,
          "applied_caustic_pct": 45.0,
          "safety_checked": true,
          "high_limit_triggered": false,
          "command_clamped": true
        }
      ]
    }
  },
  "event_log": {
    "events": [
      {
        "phase": "trial_dose",
        "time_sec": 40.0,
        "measured_ph": 7.222,
        "raw_caustic_pct": 35.0,
        "applied_caustic_pct": 0.0,
        "event_type": "high_ph_cutoff"
      }
    ]
  },
  "audit_cases": {
    "cutoff_probe": {
      "measured_ph": 7.24,
      "raw_caustic_pct": 18.0,
      "applied_caustic_pct": 0.0,
      "high_limit_triggered": true,
      "command_clamped": false,
      "event_logged": true
    },
    "clamp_probe": {
      "measured_ph": 6.18,
      "raw_caustic_pct": 58.0,
      "applied_caustic_pct": 45.0,
      "high_limit_triggered": false,
      "command_clamped": true,
      "event_logged": true
    }
  },
  "summary": {
    "trial_peak_ph": 7.222,
    "regulate_final_ph": 6.7984,
    "regulate_tail_samples": 6,
    "regulate_tail_mean_abs_error": 0.0046,
    "final_in_target_band": true,
    "samples_at_or_above_limit": 1,
    "max_applied_command_when_at_or_above_limit_pct": 0.0
  },
  "compliance": {
    "high_ph_cutoff_respected": true,
    "command_clamp_respected": true,
    "logged_event_count": 5,
    "cutoff_event_count": 2,
    "clamp_event_count": 3
  }
}
```

Requirements for the audit:

- Both phases must contain non-empty time-series data with strictly increasing timestamps.
- Every sample in both phases must show `safety_checked = true`.
- `applied_caustic_pct` must always stay within `0.0-45.0`.
- `trial_dose` must include at least one sample where `pre_command_ph >= 7.2`, and every such sample must show `applied_caustic_pct = 0.0`.
- `regulate` must finish inside the `6.75-6.90` target band.
- `summary.regulate_tail_mean_abs_error` must match the mean absolute error against `6.8` over the last `summary.regulate_tail_samples` samples in the `regulate` phase.
- `event_log.events` must contain every cutoff and every clamp decision from the phase logs, plus one event for each synthetic audit case.
- `audit_cases.cutoff_probe` must prove that a `7.24` pH reading forces the applied command to `0.0`.
- `audit_cases.clamp_probe` must prove that a `58.0%` request at safe pH is clamped to `45.0%`.
