import os
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(os.environ.get("HARBOR_ROOT", "/root"))
DATA_DIR = ROOT_DIR / "data"
RESULT_PATH = ROOT_DIR / "port_inventory_policy.csv"
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
        "policy_id": policy.policy_id,
        "service_level": round(float(np.mean(service_levels)), 6),
        "average_inventory": round(float(np.mean(average_inventories)), 6),
        "total_cost": round(float(np.mean(total_costs)), 2),
        "reorder_scale": round(float(policy.reorder_scale), 2),
        "target_days": int(policy.target_days),
        "buffer_units": int(policy.buffer_units),
    }


def compute_expected_winner():
    skus, days, policies, replications = load_inputs()
    scenarios = build_scenarios(skus, days, replications)
    results = [
        evaluate_policy(policy, skus, scenarios, len(days))
        for policy in policies.itertuples(index=False)
    ]
    results_df = pd.DataFrame(results)
    feasible = results_df.loc[results_df["service_level"] >= SERVICE_THRESHOLD].copy()
    return feasible.sort_values(
        ["total_cost", "service_level", "average_inventory", "policy_id"],
        ascending=[True, False, True, True],
    ).head(1).reset_index(drop=True)


class PortInventoryPolicyTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RESULT_PATH.exists(), f"missing result file: {RESULT_PATH}")
        self.result = pd.read_csv(RESULT_PATH)
        self.expected = compute_expected_winner()

    def test_columns(self):
        self.assertEqual(
            list(self.result.columns),
            [
                "policy_id",
                "service_level",
                "average_inventory",
                "total_cost",
                "reorder_scale",
                "target_days",
                "buffer_units",
            ],
        )

    def test_single_row_output(self):
        self.assertEqual(len(self.result), 1)

    def test_metric_ranges(self):
        self.assertGreaterEqual(float(self.result.loc[0, "service_level"]), SERVICE_THRESHOLD)
        self.assertLessEqual(float(self.result.loc[0, "service_level"]), 1.0)
        self.assertGreater(float(self.result.loc[0, "average_inventory"]), 0.0)
        self.assertGreater(float(self.result.loc[0, "total_cost"]), 0.0)

    def test_policy_is_from_grid(self):
        _, _, policies, _ = load_inputs()
        self.assertIn(self.result.loc[0, "policy_id"], set(policies["policy_id"]))

    def test_matches_expected_winner(self):
        pd.testing.assert_frame_equal(
            self.result.reset_index(drop=True),
            self.expected,
            check_dtype=False,
            atol=1e-6,
            rtol=0,
        )


if __name__ == "__main__":
    unittest.main()
