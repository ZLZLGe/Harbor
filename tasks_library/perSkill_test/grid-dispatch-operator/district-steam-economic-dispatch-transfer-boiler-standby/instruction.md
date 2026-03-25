You are preparing a one-hour standby commitment for a district steam plant during a winter morning pickup.

Read these input files:

- `/root/station_request.toml`
- `/root/boiler_fleet.csv`

Every listed boiler is already available for this hour. Choose each boiler's steam production and standby award so that all of the following hold:

1. Total scheduled steam exactly equals `steam_demand_klb_per_hr`.
2. Total scheduled standby exactly equals `standby_requirement_klb_per_hr`.
3. For every boiler, `min_steam_klb_per_hr <= steam_klb_per_hr <= max_steam_klb_per_hr`.
4. For every boiler, `0 <= standby_klb_per_hr <= standby_cap_klb_per_hr`.
5. For every boiler, `steam_klb_per_hr + standby_klb_per_hr <= max_steam_klb_per_hr`.
6. Every `steam_klb_per_hr` and `standby_klb_per_hr` value must be an integer multiple of `dispatch_step_klb_per_hr`.

Minimize combined hourly operating cost:

- Fuel cost for one boiler = `steam_klb_per_hr * incremental_heat_rate_mmbtu_per_klb * fuel_price_dollars_per_mmbtu`
- Standby carrying cost for one boiler = `standby_klb_per_hr * standby_cost_dollars_per_klb`

Write `/root/steam_commitment.toml` with this structure:

```toml
station_name = "Riverview District Steam"
interval_start = "2026-01-12T06:00:00-06:00"

[[boiler_commitment]]
boiler_id = "harbor_a"
boiler_class = "water_tube"
steam_klb_per_hr = 140.0
standby_klb_per_hr = 0.0
idle_headroom_klb_per_hr = 0.0
fuel_cost_dollars_per_hour = 1127.0
standby_cost_dollars_per_hour = 0.0

[totals]
steam_demand_klb_per_hr = 435.0
steam_dispatched_klb_per_hr = 435.0
standby_requirement_klb_per_hr = 125.0
standby_allocated_klb_per_hr = 125.0
total_fuel_cost_dollars_per_hour = 3624.25
total_standby_cost_dollars_per_hour = 68.25
total_operating_cost_dollars_per_hour = 3692.5
remaining_standby_margin_klb_per_hr = 30.0
```

Additional output requirements:

- Keep `boiler_commitment` in the same order as the rows in `boiler_fleet.csv`.
- Copy `station_name` and `interval_start` exactly from `station_request.toml`.
- Copy each boiler's `boiler_id` and `boiler_class` from `boiler_fleet.csv`.
- `idle_headroom_klb_per_hr` must equal `max_steam_klb_per_hr - steam_klb_per_hr - standby_klb_per_hr`.
- `fuel_cost_dollars_per_hour` and `standby_cost_dollars_per_hour` must match the formulas above for each boiler.
- `remaining_standby_margin_klb_per_hr` must equal the sum of all `idle_headroom_klb_per_hr` values.
- Use TOML numeric values for all steam, standby, and cost fields.
