You are preparing the next 8-week replenishment plan for a regional retail chain before the next ordering cycle closes.

Input data is under `/app/data/`:

- `planning_manifest.json`: planning window, in-scope stores, and in-scope SKUs.
- `historical_demand_weekly.csv`: weekly unit demand history for each store and SKU.
- `sku_store_setup.csv`: store and SKU demand profile, service tier, current status, and target cover.
- `inventory_snapshot.csv`: current on-hand units and committed demand by store and SKU.
- `open_purchase_orders.csv`: in-flight receipts that already have an arrival week.
- `vendor_constraints.csv`: unit cost, lead time, ordering cadence, case pack, and MOQ inputs.
- `promotion_schedule.csv`: approved promotion weeks for selected store and SKU combinations.
- `new_sku_analogs.csv`: analog mappings and launch factors for short-history items.
- `planning_policy.yaml`: forecast rules, review-capacity rules, budget rules, and risk policy.

## Your Task

1. Build an 8-week weekly forecast for every in-scope `store_id + sku_id` pair.
2. Use the provided inventory position, ordering constraints, and policy rules to determine which replenishment actions should be recommended in the current planning cycle.
3. Identify the remaining service-risk items and planning exceptions after the recommended orders are applied.
4. Write the required planning outputs to `/app/output/`.

## Business Constraints

1. Every in-scope `store_id + sku_id + week_start` combination must appear in the forecast output.
2. `historical_demand_weekly.csv`, `sku_store_setup.csv`, `inventory_snapshot.csv`, `open_purchase_orders.csv`, `vendor_constraints.csv`, `promotion_schedule.csv`, `new_sku_analogs.csv`, and `planning_policy.yaml` are the authoritative planning inputs for this task.
3. Items with `status != active` in `sku_store_setup.csv` must not receive a recommended order.
4. Recommended order quantities must respect case-pack rounding and MOQ rules.
5. Short-history items must use the provided analog mapping in the forecast and in the current-cycle planning decision.
6. The final recommended plan must stay within the budget limit defined in `planning_policy.yaml`.
7. The buying team can review at most five current-cycle recommendation lines, so the final plan must stay focused on the highest-priority lines.
8. When tradeoffs are required, protect approved near-term promotion demand and short-history launch exposure before lower-priority lines that can wait for a later cycle.

## Output

If `/app/output/` does not exist, create it first.

Write `/app/output/forecast_review.csv` with these exact columns:

```csv
store_id,sku_id,week_start,forecast_method,baseline_units,promo_lift_units,final_forecast_units,service_level,safety_stock_units,reorder_point_units
```

Requirements:

- Include one row per `store_id + sku_id + week_start`.
- `week_start` must use `YYYY-MM-DD`.
- Numeric fields must be numbers.
- `final_forecast_units` must equal `baseline_units + promo_lift_units`.

Write `/app/output/replenishment_plan.csv` with these exact columns:

```csv
store_id,sku_id,order_week_start,arrival_week_start,recommended_order_qty,inventory_position_before_order,inventory_position_after_order,coverage_weeks,decision_reason
```

Requirements:

- Include one row for every recommended order with `recommended_order_qty > 0`.
- `order_week_start` and `arrival_week_start` must use `YYYY-MM-DD`.
- `recommended_order_qty` must be a non-negative integer.
- `decision_reason` must be a short operational reason.

Write `/app/output/planning_summary.json` with this structure:

```json
{
  "planning_window": {
    "start_week": "YYYY-MM-DD",
    "end_week": "YYYY-MM-DD"
  },
  "totals": {
    "sku_store_pairs": 0,
    "forecast_rows": 0,
    "planned_orders": 0,
    "total_recommended_units": 0
  },
  "budget_check": {
    "within_budget": true,
    "budget_limit": 0.0,
    "planned_cost": 0.0
  },
  "service_risk_items": [
    {
      "store_id": "STORE_1",
      "sku_id": "SKU_1",
      "risk_level": "high",
      "reason": "Example"
    }
  ],
  "exceptions": [
    {
      "store_id": "STORE_1",
      "sku_id": "SKU_1",
      "exception_code": "budget_hold",
      "detail": "Example"
    }
  ],
  "notes": [
    "Example note"
  ]
}
```

Requirements:

- `forecast_rows` must match the number of rows in `forecast_review.csv`.
- `planned_orders` must match the number of rows in `replenishment_plan.csv`.
- `within_budget` must reflect the final plan against `planning_policy.yaml`.
- `service_risk_items` must include every material remaining risk after planning.

Write `/app/output/planner_memo.md`.

The memo must include:

- the planning window;
- the number of planned orders;
- total recommended units;
- the main budget and vendor constraints;
- the short-history assumption for `SKU-FOXTROT`;
- how open purchase orders affected the current-cycle plan;
- the main remaining service risks;
- the major tradeoffs in the final plan.

## Notes

- Do not modify files under `/app/data/`.
- Do not modify tests, verifier files, task metadata, or environment files.
- Do not replace the requested planning workflow with hardcoded final answers, cached outputs, or fabricated calculations.
- You may write helper scripts in the working directory, but the only required deliverables are the four files under `/app/output/`.
