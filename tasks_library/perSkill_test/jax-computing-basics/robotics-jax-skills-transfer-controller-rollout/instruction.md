You are validating a batched robot controller rollout in `/app`.

Read these inputs:

- `/app/data/controller_bundle.npz`
  - `initial_states`: shape `(batch, 4)`
  - `nominal_controls`: shape `(batch, steps, 2)`
  - `disturbances`: shape `(batch, steps, 4)`
  - `goal_states`: shape `(batch, 4)`
- `/app/data/dynamics_params.npz`
  - `A`: shape `(4, 4)`
  - `B`: shape `(4, 2)`
  - `K`: shape `(2, 4)`
  - `bias`: shape `(4,)`
- `/app/data/cost_weights.npy`
  - the first 4 entries are state weights `q`
  - the last 2 entries are control weights `r`

For each trajectory `i` and each time step `t`, start from `x_0 = initial_states[i]` and compute:

1. `feedback_t = (goal_states[i] - x_t) @ K.T`
2. `u_t = nominal_controls[i, t] + feedback_t`
3. `x_{t+1} = tanh(x_t @ A.T + u_t @ B.T + disturbances[i, t] + bias) + 0.05 * x_t`

Collect every state including the initial state and save the full tensor with shape `(batch, steps + 1, 4)` to `/app/robot_rollout.npy`.

Then compute per-trajectory rollout costs using each post-transition state `x_{t+1}` and the matching `u_t`:

- `tracking_cost = sum_t sum(q * (x_{t+1} - goal_states[i])^2)`
- `control_cost = sum_t sum(r * u_t^2)`

Save `/app/control_cost_summary.npy` as a shape `(batch, 3)` array whose columns are:

1. `tracking_cost`
2. `control_cost`
3. `tracking_cost + control_cost`

Implement the rollout in JAX for all trajectories. The primary output file is `/app/robot_rollout.npy`.
