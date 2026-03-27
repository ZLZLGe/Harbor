You are tuning a coupled 3-reservoir level controller with persistent leakage and valve bias.

Input file:
- `/root/transfer2_reservoir_case.json`

Run the complete simulation horizon with:
1. The nominal correction defined in the input data.
2. An additional bounded decayed error-memory correction term.

Write:
1. `/root/transfer2_reservoir_trace.json`
2. `/root/transfer2_reservoir_stability.json`

Trace format (`/root/transfer2_reservoir_trace.json`):
- `records`: one per timestep.
- Each record includes:
  - `k` (integer)
  - `reference` (3 floats)
  - `level` (3 floats)
  - `u_nominal` (3 floats)
  - `integral` (3 floats)
  - `u_total` (3 floats)

Report format (`/root/transfer2_reservoir_stability.json`):
- `scenario`: string
- `controller`:
  - `gamma` (float)
  - `c_i` (3 floats)
  - `max_integral` (3 floats)
- `baseline_tail_rmse` (float)
- `controlled_tail_rmse` (float)
- `improvement_ratio` (float, defined as `1 - controlled_tail_rmse / baseline_tail_rmse`)
- `overshoot_per_tank` (3 floats)
- `integral_energy` (float)
- `trace_file` (string, exactly `/root/transfer2_reservoir_trace.json`)

Rules:
1. Respect the coupling matrix in the input dynamics.
2. Apply integral bounds at each step.
3. `records` must contain exactly `steps` items.
4. Compute all metrics from generated trajectory data.
