You are producing a scenario risk sheet in `/app`.

Read these inputs:

- `/app/data/portfolio_book.npz`
  - `strike`: strike for each option position
  - `maturity_years`: time to expiry for each position
  - `base_vol`: baseline implied volatility for each position
  - `vol_beta`: multiplier applied to the scenario volatility shift
  - `base_rate`: baseline risk-free rate for each position
  - `option_type`: `1` for a call, `-1` for a put
  - `quantity`: number of contracts in the portfolio
- `/app/data/scenario_grid.npz`
  - `spot`: spot level for each market scenario
  - `vol_shift`: common volatility shift for each scenario
  - `rate_shift`: common rate shift for each scenario

For each scenario `j` and position `i`, define:

- `sigma_ij = base_vol[i] + vol_beta[i] * vol_shift[j]`
- `rate_ij = base_rate[i] + rate_shift[j]`
- `tau_i = maturity_years[i]`
- `d1_ij = (log(spot[j] / strike[i]) + (rate_ij + 0.5 * sigma_ij^2) * tau_i) / (sigma_ij * sqrt(tau_i))`
- `d2_ij = d1_ij - sigma_ij * sqrt(tau_i)`
- `price_ij = option_type[i] * (spot[j] * N(option_type[i] * d1_ij) - strike[i] * exp(-rate_ij * tau_i) * N(option_type[i] * d2_ij))`

Here `N(.)` is the standard normal CDF and there are no dividends.

Aggregate the portfolio value for scenario `j` as:

- `V_j = sum_i quantity[i] * price_ij`

Using automatic differentiation on the scalar portfolio function `V(spot, vol_shift, rate_shift)`, compute one output row per scenario with these five columns in exactly this order:

1. `V_j`
2. `delta_j = dV / dspot`
3. `gamma_j = d^2 V / dspot^2`
4. `vega_j = dV / dvol_shift`
5. `rho_j = dV / drate_shift`

Implement the computation in JAX, batch all scenarios with vectorization, JIT-compile the batched evaluation, and save the final array with shape `(num_scenarios, 5)` to `/app/portfolio_greeks.npy`.

The primary output file is `/app/portfolio_greeks.npy`.
