# Transfer | Port Inventory Policy Monte Carlo

## Task

You are given a port-maintenance spare-parts portfolio, a calendar of demand pressure factors, a Monte Carlo replication table, and a catalog of candidate replenishment policies.

Evaluate every policy, keep only policies whose simulated mean service level is at least `0.990000`, and write the single lowest-cost feasible policy to `/root/port_inventory_policy.csv`.

## Data

Files are in `/root/data/`:

- `sku_catalog.csv`
  - one row per spare part SKU
  - row order defines `sku_index` (`0`-based) for the random-number rules below
- `day_factors.csv`
  - one row per simulated day, already in chronological order
- `replications.csv`
  - one row per Monte Carlo replication
- `policy_grid.csv`
  - one row per candidate policy

## Random Number Rules

Use NumPy's `Generator(PCG64(...))`.

For one replication and one SKU:

1. Let `sku_index` be the row index of that SKU in `sku_catalog.csv`, starting at `0`.
2. Build:
   - `demand_rng = np.random.Generator(np.random.PCG64(demand_seed + 100003 * sku_index))`
   - `delay_rng = np.random.Generator(np.random.PCG64(delay_seed + 200003 * sku_index))`
3. Pre-sample:
   - `daily_demand[day]` from a Poisson distribution
   - `daily_delay_uniform[day] = delay_rng.random(...)`

For day `d` from `day_factors.csv`:

```text
expected_demand =
    base_daily_demand
    * demand_multiplier
    * (1 + congestion_uplift * congestion_flag)
```

Then sample:

```text
daily_demand[d] ~ Poisson(expected_demand)
```

## Policy Mechanics

For one policy and one SKU:

```text
reorder_point = ceil(base_daily_demand * lead_time_days * reorder_scale + buffer_units)
order_up_to   = ceil(reorder_point + base_daily_demand * target_days)
```

Simulate each replication independently for all days in `day_factors.csv`.

Per SKU, track:

- `on_hand`, initialized from `initial_inventory`
- outstanding replenishment orders, each with `arrival_day` and `quantity`

Within one day, process events in this exact order:

1. Receive every outstanding order whose `arrival_day` equals the current day number.
2. Realize that day's demand.
3. `filled = min(on_hand, demand)` and `lost = demand - filled`
4. Lost demand disappears immediately; do not backorder it.
5. Charge stockout cost: `lost * stockout_penalty`
6. Charge holding cost on ending inventory: `on_hand * holding_cost_per_day`
7. Compute:

   ```text
   inventory_position = on_hand + sum(quantity of all outstanding orders)
   ```

8. If `inventory_position <= reorder_point`, place exactly one order with:

   ```text
   quantity = order_up_to - inventory_position
   ```

   if `quantity > 0`.

When an order is placed on day `d`, its arrival day is:

```text
d + lead_time_days + extra_delay_days
```

where:

- `extra_delay_days = delay_extra_days` if `daily_delay_uniform[d] < delay_probability`
- otherwise `extra_delay_days = 0`

Charge purchase and ordering cost at order placement time:

```text
quantity * unit_cost + order_cost
```

If an order's arrival day is after the final simulated day, it is never received during the horizon, but its purchase and ordering cost still count.

## Aggregation

For one replication:

- `service_level = total_filled_demand / total_realized_demand`
- `average_inventory = mean(end_of_day_on_hand)` across every SKU-day cell
- `total_cost = purchase_cost + ordering_cost + holding_cost + stockout_cost`

For one policy, average those three replication-level metrics over all rows in `replications.csv`.

## Selection Rule

Keep only policies with:

```text
service_level >= 0.990000
```

Choose the winner by:

1. `total_cost` ascending
2. `service_level` descending
3. `average_inventory` ascending
4. `policy_id` ascending

## Output

Write exactly one row to `/root/port_inventory_policy.csv` with this exact header:

```csv
policy_id,service_level,average_inventory,total_cost,reorder_scale,target_days,buffer_units
```

Formatting rules:

- round `service_level` and `average_inventory` to 6 decimal places
- round `total_cost` to 2 decimal places
- round `reorder_scale` to 2 decimal places
- keep `target_days` and `buffer_units` as integers
