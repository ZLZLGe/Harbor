#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed


DATA_DIR = Path("/root/data")
OUTPUT_PATH = Path("/root/port_inventory_policy.csv")
SERVICE_THRESHOLD = 0.99


def load_inputs():
    skus = pd.read_csv(DATA_DIR / "sku_catalog.csv")
    days = pd.read_csv(DATA_DIR / "day_factors.csv")
    policies = pd.read_csv(DATA_DIR / "policy_grid.csv")
    replications = pd.read_csv(DATA_DIR / "replications.csv")
    return skus, days, policies, replications


def build_scenarios(skus, days, replications):
    day_multipliers = days["demand_multiplier"].to_numpy(float)
    congestion_flags = days["congestion_flag"].to_numpy(int)
    scenarios = []

    for replication in replications.itertuples(index=False):
        sku_scenarios = []
        for sku_index, sku in enumerate(skus.itertuples(index=False)):
            demand_rng = np.random.Generator(
                np.random.PCG64(int(replication.demand_seed) + 100003 * sku_index)
            )
            delay_rng = np.random.Generator(
                np.random.PCG64(int(replication.delay_seed) + 200003 * sku_index)
            )
            mean_demand = (
                sku.base_daily_demand
                * day_multipliers
                * (1.0 + sku.congestion_uplift * congestion_flags)
            )
            sku_scenarios.append(
                {
                    "sku_id": sku.sku_id,
                    "demand": demand_rng.poisson(mean_demand),
                    "delay_uniform": delay_rng.random(len(days)),
                }
            )
        scenarios.append(sku_scenarios)

    return scenarios


def evaluate_policy(policy, skus, scenarios, horizon):
    service_levels = []
    average_inventories = []
    total_costs = []

    policy_row = policy._asdict()

    for scenario in scenarios:
        total_demand = 0
        total_filled = 0
        total_cost = 0.0
        inventory_sum = 0.0
        inventory_cells = 0

        for sku, sku_scenario in zip(skus.itertuples(index=False), scenario):
            on_hand = int(sku.initial_inventory)
            outstanding_orders = []

            reorder_point = int(
                np.ceil(
                    sku.base_daily_demand * sku.lead_time_days * policy.reorder_scale
                    + policy.buffer_units
                )
            )
            order_up_to = int(
                np.ceil(reorder_point + sku.base_daily_demand * policy.target_days)
            )

            for day_index in range(horizon):
                current_day = day_index + 1

                arrivals = sum(
                    quantity
                    for arrival_day, quantity in outstanding_orders
                    if arrival_day == current_day
                )
                if arrivals:
                    on_hand += arrivals
                outstanding_orders = [
                    (arrival_day, quantity)
                    for arrival_day, quantity in outstanding_orders
                    if arrival_day != current_day
                ]

                demand = int(sku_scenario["demand"][day_index])
                filled = min(on_hand, demand)
                lost = demand - filled
                on_hand -= filled

                total_demand += demand
                total_filled += filled
                total_cost += lost * sku.stockout_penalty
                total_cost += on_hand * sku.holding_cost_per_day

                inventory_sum += on_hand
                inventory_cells += 1

                inventory_position = on_hand + sum(
                    quantity for _, quantity in outstanding_orders
                )
                if inventory_position <= reorder_point:
                    quantity = max(order_up_to - inventory_position, 0)
                    if quantity > 0:
                        extra_delay_days = (
                            sku.delay_extra_days
                            if sku_scenario["delay_uniform"][day_index] < sku.delay_probability
                            else 0
                        )
                        arrival_day = current_day + sku.lead_time_days + extra_delay_days
                        outstanding_orders.append((arrival_day, int(quantity)))
                        total_cost += quantity * sku.unit_cost + sku.order_cost

        service_levels.append(total_filled / total_demand)
        average_inventories.append(inventory_sum / inventory_cells)
        total_costs.append(total_cost)

    return {
        "policy_id": policy_row["policy_id"],
        "service_level": round(float(np.mean(service_levels)), 6),
        "average_inventory": round(float(np.mean(average_inventories)), 6),
        "total_cost": round(float(np.mean(total_costs)), 2),
        "reorder_scale": round(float(policy_row["reorder_scale"]), 2),
        "target_days": int(policy_row["target_days"]),
        "buffer_units": int(policy_row["buffer_units"]),
    }


def main():
    skus, days, policies, replications = load_inputs()
    scenarios = build_scenarios(skus, days, replications)

    results = Parallel(n_jobs=-1, verbose=10)(
        delayed(evaluate_policy)(policy, skus, scenarios, len(days))
        for policy in policies.itertuples(index=False)
    )

    results_df = pd.DataFrame(results)
    feasible = results_df.loc[results_df["service_level"] >= SERVICE_THRESHOLD].copy()
    winner = feasible.sort_values(
        ["total_cost", "service_level", "average_inventory", "policy_id"],
        ascending=[True, False, True, True],
    ).head(1)

    winner.to_csv(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
PY
