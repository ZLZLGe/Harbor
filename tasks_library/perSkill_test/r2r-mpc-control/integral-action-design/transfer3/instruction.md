You are evaluating a two-axis rewinder pair that tracks cyclic force setpoints under constant actuator bias.

Input file:
- `/root/transfer3_winder_case.json`

Simulate the full horizon with:
1. The nominal correction from the case data.
2. A bounded decayed error-memory augmentation.

Write:
1. `/root/transfer3_winder_trace.json`
2. `/root/transfer3_winder_quality.json`

`/root/transfer3_winder_trace.json`:
- `records`: array with one entry per step.
- Each entry includes:
  - `k` (integer)
  - `reference` (2 floats)
  - `state` (2 floats)
  - `u_nominal` (2 floats)
  - `integral` (2 floats)
  - `u_total` (2 floats)

`/root/transfer3_winder_quality.json`:
- `scenario`: string
- `controller`:
  - `gamma` (float)
  - `c_i` (2 floats)
  - `max_integral` (2 floats)
- `baseline_cycle_mae` (float)
- `controlled_cycle_mae` (float)
- `improvement_ratio` (float, defined as `1 - controlled_cycle_mae / baseline_cycle_mae`)
- `control_effort_l1` (float)
- `integral_saturation_fraction` (float in [0, 1])
- `trace_file` (string, exactly `/root/transfer3_winder_trace.json`)

Rules:
1. Build per-step references using the cycle definition from input.
2. Enforce integral clipping every step.
3. `records` must contain exactly `steps` entries.
4. Compute all reported metrics from generated trace values.
