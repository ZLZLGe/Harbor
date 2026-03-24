Implement a deterministic battery peak-shaving replay for a commercial facility. All operating thresholds, tariff windows, reserve rules, and dispatch preferences must be loaded from the provided nested configuration file at runtime, and the final dispatch artifact must be written in the same structured format. Do not hard-code tariff labels, prices, demand-charge rates, reserve floors, demand caps, or battery limits.

This task is a rule replay, not a search problem. For each hour, apply exactly one action in this priority order:

1. Precharge when the current hour falls inside a configured precharge window and the current state of charge is below that window's target.
2. Otherwise discharge only when the current tariff label appears in the configured support windows and facility load is above the configured demand cap.
3. Otherwise idle.

Create these files:

`dispatch_scheduler.py`
- Define class `BatteryPeakShavingScheduler`.
- Constructor: `__init__(self, config)` where `config` is the nested dict loaded from `battery_constraints.yaml` under the top-level `battery_peak_shaving` key.
- Methods:
  - `reset()`
  - `tariff_for_hour(hour)` returning the tariff label string for that hour
  - `reserve_floor_for_hour(hour)` returning the minimum required state of charge in MWh for that hour
  - `dispatch_hour(hour, facility_load_kw)` returning a dict with keys:
    - `tariff_label`
    - `battery_power_kw`
    - `grid_power_kw`
    - `soc_mwh`
    - `reserve_floor_mwh`
    - `action`

Use these exact dispatch rules:

- Interpret tariff windows with `start_hour <= hour < end_hour`. Return the label from the first matching tariff window.
- Interpret `reserve_floor_for_hour(hour)` as the maximum of:
  - `reserve.terminal_min_soc_mwh`
  - every `reserve.critical_windows[*].min_soc_mwh` whose `end_hour` is greater than the queried hour
- Use the sign convention: positive `battery_power_kw` means the battery is discharging into the facility load, negative means the battery is charging from the grid.
- During precharge, choose charge power as the largest feasible value subject to all of these limits:
  - battery `max_charge_power_kw`
  - energy needed to reach the active precharge target in the current step
  - when export is not allowed, remaining headroom under the configured demand cap for that hour
- During support discharge, choose discharge power as the largest feasible value subject to all of these limits:
  - battery `max_discharge_power_kw`
  - the amount needed to reduce grid power down to the configured demand cap
  - energy available above the active reserve floor in the current step
- Update state of charge with the configured efficiencies:
  - charging adds `charge_power_kw * charge_efficiency * dt_hours / 1000`
  - discharging subtracts `discharge_power_kw * dt_hours / discharge_efficiency / 1000`
- Clamp state of charge to the configured min and max battery bounds after each hour.
- Compute `grid_power_kw` as `facility_load_kw - battery_power_kw`, then clamp it to `0` when export is not allowed.
- `action` must be exactly one of `charge`, `discharge`, or `idle`.
- Round numeric values returned by `dispatch_hour` to 4 decimal places.

`battery_peak_shaving.py`
- Load `battery_constraints.yaml` and `facility_load.csv` at runtime.
- Replay every row in `facility_load.csv` in hour order.
- Do not modify the provided input files.
- Write these outputs:
  - `battery_dispatch_plan.yaml`
  - `battery_dispatch_results.csv`
  - `battery_summary.md`

Input files:
- `battery_constraints.yaml`
- `facility_load.csv`

`battery_constraints.yaml` contains nested sections for:
- site metadata and hourly step size
- tariff windows and energy prices
- demand charge settings
- battery power, energy, and efficiency constraints
- reserve requirements
- dispatch preferences

`facility_load.csv` columns:
- `hour`
- `facility_load_kw`

Replay requirements:
- Duration: 24 hourly steps
- Keep grid power non-negative because export is not allowed
- Reach the configured precharge target as early as limits allow inside the configured precharge window
- Shave load toward the configured demand cap during allowed support hours while still respecting the active reserve floor
- Final state of charge must stay above the configured terminal reserve
- Optimized peak demand must be no higher than the configured demand cap
- Optimized total cost must be lower than baseline total cost

Summary calculations:
- `baseline_energy_cost_usd` is the sum over all hours of `facility_load_kw * dt_hours / 1000 * tariff_price`
- `optimized_energy_cost_usd` is the sum over all hours of `grid_power_kw * dt_hours / 1000 * tariff_price`
- Demand charge is `daily_peak_kw * demand_charge_usd_per_kw`
- `baseline_total_cost_usd` is baseline energy cost plus baseline demand charge
- `optimized_total_cost_usd` is optimized energy cost plus optimized demand charge
- `cost_savings_usd` is baseline total cost minus optimized total cost
- `peak_reduction_kw` is baseline peak minus optimized peak
- `total_charge_mwh` and `total_discharge_mwh` are the sums of hourly battery power magnitudes before efficiency loss is applied to state of charge
- `reserve_respected` is true only if every output row finishes with `soc_mwh >= reserve_floor_mwh`
- `export_respected` is true only if every output row has `grid_power_kw >= 0`
- Round all summary metrics to 4 decimal places, except booleans and integer counters

`battery_dispatch_plan.yaml` must use this nested structure:

```yaml
simulation:
  site_name: <string>
  rows_processed: <int>
  dt_hours: <float>
summary:
  baseline_energy_cost_usd: <float>
  optimized_energy_cost_usd: <float>
  baseline_demand_charge_usd: <float>
  optimized_demand_charge_usd: <float>
  baseline_total_cost_usd: <float>
  optimized_total_cost_usd: <float>
  cost_savings_usd: <float>
  baseline_peak_kw: <float>
  optimized_peak_kw: <float>
  peak_reduction_kw: <float>
  total_charge_mwh: <float>
  total_discharge_mwh: <float>
  final_soc_mwh: <float>
  reserve_respected: <bool>
  export_respected: <bool>
dispatch_plan:
  - hour: <int>
    tariff_label: <string>
    facility_load_kw: <float>
    battery_power_kw: <float>
    grid_power_kw: <float>
    soc_mwh: <float>
    reserve_floor_mwh: <float>
    action: <string>
```

`battery_dispatch_results.csv` requirements:
- Exactly the same number of rows as `facility_load.csv`
- Exact column order:

```csv
hour,tariff_label,facility_load_kw,battery_power_kw,grid_power_kw,soc_mwh,reserve_floor_mwh,action
```

`battery_summary.md` must include short sections covering:
- system design
- dispatch strategy
- results summary
