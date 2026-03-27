You are auditing a 6-section web-tension line model with persistent disturbances.

Input file:
- `/root/similar_line_case.json`

Run the closed-loop simulation for all timesteps in the case file.
Use the nominal correction described by the case data and augment it with a bounded, decayed error-memory term so that steady-state bias is reduced after the section-3 setpoint change.

Write these output files:
1. `/root/similar_tension_trace.json`
2. `/root/similar_tension_offset_report.json`

`/root/similar_tension_trace.json` must be JSON with:
- `records`: array of timestep entries, one per step.
- Each entry must include:
  - `k` (integer step index)
  - `reference` (6 floats)
  - `state` (6 floats)
  - `u_mpc` (6 floats)
  - `integral` (6 floats)
  - `u_total` (6 floats)

`/root/similar_tension_offset_report.json` must be JSON with:
- `scenario`: string
- `controller`:
  - `gamma` (float)
  - `c_i` (array of 6 floats)
  - `max_integral` (array of 6 floats)
- `kpis`:
  - `baseline_tail_mae` (float)
  - `controlled_tail_mae` (float)
  - `improvement_ratio` (float, defined as `1 - controlled_tail_mae / baseline_tail_mae`)
  - `max_abs_integral` (float)
- `final_state` (6 floats)
- `final_reference` (6 floats)
- `trace_file` (string, exactly `/root/similar_tension_trace.json`)

Rules:
1. Use only values from the input case file for model and controller parameters.
2. Enforce the configured integral bounds at every step.
3. `records` length must exactly match `steps`.
4. Compute all metrics from your generated trace.
