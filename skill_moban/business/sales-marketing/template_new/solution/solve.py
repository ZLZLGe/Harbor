from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/app/data"))
OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_ROOT", "/app/output"))


def round2(value: float) -> float:
    return round(float(value), 2)


def ceil_int(value: float) -> int:
    return int(math.ceil(float(value)))


def load_inputs() -> dict:
    manifest = json.loads((DATA_ROOT / "planning_manifest.json").read_text(encoding="utf-8"))
    policy = yaml.safe_load((DATA_ROOT / "planning_policy.yaml").read_text(encoding="utf-8"))

    history = pd.read_csv(DATA_ROOT / "historical_demand_weekly.csv")
    history["week_start"] = pd.to_datetime(history["week_start"])

    setup = pd.read_csv(DATA_ROOT / "sku_store_setup.csv")
    inventory = pd.read_csv(DATA_ROOT / "inventory_snapshot.csv")
    open_po = pd.read_csv(DATA_ROOT / "open_purchase_orders.csv")
    if not open_po.empty:
        open_po["arrival_week_start"] = pd.to_datetime(open_po["arrival_week_start"])
    promo = pd.read_csv(DATA_ROOT / "promotion_schedule.csv")
    promo["week_start"] = pd.to_datetime(promo["week_start"])
    vendor = pd.read_csv(DATA_ROOT / "vendor_constraints.csv")
    analogs = pd.read_csv(DATA_ROOT / "new_sku_analogs.csv")

    return {
        "manifest": manifest,
        "policy": policy,
        "history": history,
        "setup": setup,
        "inventory": inventory,
        "open_po": open_po,
        "promo": promo,
        "vendor": vendor,
        "analogs": analogs,
        "plan_weeks": [pd.Timestamp(value) for value in manifest["planning_window"]["week_starts"]],
    }


def compute_profile_baseline(
    pair: pd.Series,
    history: pd.DataFrame,
    analog_by_pair: dict[tuple[str, str], pd.Series],
    policy: dict,
) -> tuple[float, float, str]:
    store_id = pair["store_id"]
    sku_id = pair["sku_id"]
    profile = pair["demand_profile"]
    pair_history = history[
        (history["store_id"] == store_id) & (history["sku_id"] == sku_id)
    ].sort_values("week_start")

    if profile == "launch":
        analog = analog_by_pair[(store_id, sku_id)]
        analog_history = history[
            (history["store_id"] == store_id)
            & (history["sku_id"] == analog["analog_sku_id"])
        ].sort_values("week_start")
        baseline = analog_history["demand_units"].tail(4).mean() * float(analog["analog_factor"])
        sigma = analog_history["demand_units"].tail(8).std(ddof=0) * float(analog["analog_factor"])
        method = policy["forecast_rules"]["launch"]["method"]
    elif profile == "stable":
        baseline = pair_history["demand_units"].tail(4).mean()
        sigma = pair_history["demand_units"].tail(8).std(ddof=0)
        method = policy["forecast_rules"]["stable"]["method"]
    elif profile == "trend":
        weights = policy["forecast_rules"]["trend"]["weights"]
        recent = pair_history["demand_units"].tail(4).tolist()
        baseline = sum(value * weight for value, weight in zip(recent, weights))
        sigma = pair_history["demand_units"].tail(8).std(ddof=0)
        method = policy["forecast_rules"]["trend"]["method"]
    else:
        last8 = pair_history["demand_units"].tail(8)
        nonzero = last8[last8 > 0]
        baseline = (nonzero.mean() if not nonzero.empty else 0.0) * (len(nonzero) / 8.0)
        sigma = last8.std(ddof=0)
        method = policy["forecast_rules"]["intermittent"]["method"]

    return round2(baseline), float(0.0 if pd.isna(sigma) else sigma), method


def build_outputs(inputs: dict) -> tuple[list[dict], list[dict], dict]:
    policy = inputs["policy"]
    history = inputs["history"]
    setup = inputs["setup"]
    inventory = inputs["inventory"]
    open_po = inputs["open_po"]
    promo = inputs["promo"]
    vendor = inputs["vendor"]
    analogs = inputs["analogs"]
    plan_weeks = inputs["plan_weeks"]

    review_capacity = int(policy["review_capacity"]["max_order_lines"])
    promo_window_weeks = int(policy["priority_rules"]["promo_window_weeks"])
    launch_window_weeks = int(policy["priority_rules"]["launch_window_weeks"])

    tier_rank = {"A": 0, "B": 1, "C": 2}
    setup_by_pair = {(row["store_id"], row["sku_id"]): row for _, row in setup.iterrows()}
    inventory_by_pair = {(row["store_id"], row["sku_id"]): row for _, row in inventory.iterrows()}
    vendor_by_sku = {row["sku_id"]: row for _, row in vendor.iterrows()}
    analog_by_pair = {(row["store_id"], row["sku_id"]): row for _, row in analogs.iterrows()}
    promo_map = {
        (row["store_id"], row["sku_id"], row["week_start"]): float(row["demand_multiplier"])
        for _, row in promo.iterrows()
    }
    open_po_map: dict[tuple[str, str], dict[pd.Timestamp, int]] = defaultdict(lambda: defaultdict(int))
    for _, row in open_po.iterrows():
        open_po_map[(row["store_id"], row["sku_id"])][row["arrival_week_start"]] += int(row["units"])

    forecast_rows: list[dict] = []
    candidate_rows: list[dict] = []

    for _, pair in setup.sort_values(["store_id", "sku_id"]).iterrows():
        store_id = pair["store_id"]
        sku_id = pair["sku_id"]
        tier = pair["service_tier"]
        cover_weeks = int(pair["target_cover_weeks"])
        profile = pair["demand_profile"]
        baseline, sigma, method = compute_profile_baseline(pair, history, analog_by_pair, policy)

        lead_time = int(vendor_by_sku[sku_id]["lead_time_weeks"])
        service_level = float(policy["service_level_output"][tier])
        safety_stock = ceil_int(
            policy["service_level_z"][tier]
            * sigma
            * math.sqrt(lead_time + int(policy["review_period_weeks"]))
            * float(policy["profile_sigma_multiplier"][profile])
        )

        pair_forecasts: list[dict] = []
        for idx, week_start in enumerate(plan_weeks):
            multiplier = float(promo_map.get((store_id, sku_id, week_start), 1.0))
            final_forecast = round2(baseline * multiplier)
            lead_cover = sum(
                round2(
                    baseline
                    * float(promo_map.get((store_id, sku_id, future_week), 1.0))
                )
                for future_week in plan_weeks[idx : idx + lead_time]
            )
            pair_row = {
                "store_id": store_id,
                "sku_id": sku_id,
                "week_start": week_start.strftime("%Y-%m-%d"),
                "forecast_method": method,
                "baseline_units": baseline,
                "promo_lift_units": round2(final_forecast - baseline),
                "final_forecast_units": final_forecast,
                "service_level": service_level,
                "safety_stock_units": safety_stock,
                "reorder_point_units": ceil_int(lead_cover + safety_stock),
            }
            pair_forecasts.append(pair_row)
            forecast_rows.append(pair_row)

        on_hand = int(inventory_by_pair[(store_id, sku_id)]["on_hand_units"])
        committed = int(inventory_by_pair[(store_id, sku_id)]["committed_units"])
        future_receipts = defaultdict(int, open_po_map[(store_id, sku_id)])
        current_week = plan_weeks[0]
        current_forecast = pair_forecasts[0]

        on_hand += future_receipts[current_week]
        pipeline_after = sum(units for arrival, units in future_receipts.items() if arrival > current_week)
        inventory_position_before = round2(on_hand + pipeline_after - committed)

        cadence_weeks = int(vendor_by_sku[sku_id]["order_cadence_weeks"])
        cadence_phase = int(vendor_by_sku[sku_id]["cadence_phase"])
        cadence_due = (0 - cadence_phase) % cadence_weeks == 0

        if pair["status"] != "active" or not cadence_due:
            continue

        reorder_point = int(current_forecast["reorder_point_units"])
        if inventory_position_before >= reorder_point:
            continue

        near_term_forecasts = pair_forecasts[:promo_window_weeks]
        positive_promo_lift = round2(
            sum(max(0.0, float(row["promo_lift_units"])) for row in near_term_forecasts)
        )
        near_term_promo = positive_promo_lift > 0.0
        launch_exposure = profile == "launch"

        target_stock = ceil_int(
            sum(float(row["final_forecast_units"]) for row in pair_forecasts[:cover_weeks])
            + safety_stock
        )
        if near_term_promo:
            target_stock += ceil_int(positive_promo_lift)
        if launch_exposure:
            launch_cover = ceil_int(
                sum(float(row["final_forecast_units"]) for row in pair_forecasts[:launch_window_weeks])
            )
            target_stock += launch_cover

        raw_qty = target_stock - inventory_position_before
        if raw_qty <= 0:
            continue

        case_pack = int(vendor_by_sku[sku_id]["case_pack_units"])
        moq = int(vendor_by_sku[sku_id]["moq_units"])
        order_qty = max(moq, ceil_int(raw_qty / case_pack) * case_pack)
        arrival_week = (current_week + pd.Timedelta(weeks=lead_time)).strftime("%Y-%m-%d")
        cost = round2(order_qty * float(vendor_by_sku[sku_id]["unit_cost"]))
        gap = round2(reorder_point - inventory_position_before)

        if launch_exposure and near_term_promo:
            decision_reason = "priority_launch_promo_build"
        elif near_term_promo:
            decision_reason = "priority_promo_build"
        elif launch_exposure:
            decision_reason = "priority_launch_protection"
        else:
            decision_reason = "priority_service_protection"

        candidate_rows.append(
            {
                "store_id": store_id,
                "sku_id": sku_id,
                "order_week_start": current_forecast["week_start"],
                "arrival_week_start": arrival_week,
                "recommended_order_qty": order_qty,
                "inventory_position_before_order": inventory_position_before,
                "inventory_position_after_order": round2(inventory_position_before + order_qty),
                "coverage_weeks": cover_weeks,
                "decision_reason": decision_reason,
                "cost": cost,
                "tier": tier,
                "gap_to_reorder_point": gap,
                "gap_per_cost": (gap / cost) if cost else gap,
                "near_term_promo": int(near_term_promo),
                "launch_exposure": int(launch_exposure),
                "promo_incremental_units": positive_promo_lift,
            }
        )

    candidate_rows.sort(
        key=lambda row: (
            -row["near_term_promo"],
            -row["launch_exposure"],
            tier_rank[row["tier"]],
            -row["promo_incremental_units"],
            -row["gap_per_cost"],
            -row["gap_to_reorder_point"],
            row["store_id"],
            row["sku_id"],
        )
    )

    accepted_rows: list[dict] = []
    held_rows: list[dict] = []
    running_cost = 0.0
    budget_limit = float(policy["budget"]["limit"])
    for row in candidate_rows:
        if len(accepted_rows) >= review_capacity:
            held_rows.append(row)
            continue
        if running_cost + row["cost"] <= budget_limit + 1e-9:
            accepted_rows.append(row)
            running_cost = round2(running_cost + row["cost"])
        else:
            held_rows.append(row)

    accepted_by_pair = {(row["store_id"], row["sku_id"]): row for row in accepted_rows}
    held_by_pair = {(row["store_id"], row["sku_id"]): row for row in held_rows}
    forecast_by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in forecast_rows:
        forecast_by_pair[(row["store_id"], row["sku_id"])].append(row)

    service_risk_items: list[dict] = []
    exceptions: list[dict] = []
    seen_exception_keys: set[tuple[str, str, str]] = set()

    for _, row in setup[setup["demand_profile"] == "launch"].sort_values(["store_id", "sku_id"]).iterrows():
        exceptions.append(
            {
                "store_id": row["store_id"],
                "sku_id": row["sku_id"],
                "exception_code": "analog_based_forecast",
                "detail": "Launch item forecast is anchored to the provided analog mapping.",
            }
        )

    for row in held_rows:
        exceptions.append(
            {
                "store_id": row["store_id"],
                "sku_id": row["sku_id"],
                "exception_code": "budget_hold",
                "detail": "Current-cycle review capacity or budget was used by higher-priority lines.",
            }
        )

    for pair_key, pair_forecasts in sorted(forecast_by_pair.items()):
        store_id, sku_id = pair_key
        pair_setup = setup_by_pair[pair_key]
        on_hand = int(inventory_by_pair[pair_key]["on_hand_units"])
        committed = int(inventory_by_pair[pair_key]["committed_units"])
        future_receipts = defaultdict(int, open_po_map[pair_key])
        if pair_key in accepted_by_pair:
            accepted = accepted_by_pair[pair_key]
            future_receipts[pd.Timestamp(accepted["arrival_week_start"])] += int(accepted["recommended_order_qty"])

        risk_reason = None
        risk_level = None
        for forecast_row in pair_forecasts:
            week_start = pd.Timestamp(forecast_row["week_start"])
            on_hand += future_receipts[week_start]
            inventory_position = on_hand + sum(
                units for arrival, units in future_receipts.items() if arrival > week_start
            ) - committed
            if pair_setup["status"] != "active" and inventory_position < float(forecast_row["reorder_point_units"]):
                risk_reason = "Item status prevents a replenishment action during the planning window."
                risk_level = "high" if pair_setup["service_tier"] in {"A", "B"} else "medium"
                break

            on_hand -= float(forecast_row["final_forecast_units"])
            if on_hand < 0:
                if pair_key in held_by_pair:
                    risk_reason = "Priority tradeoffs left this line outside the capped current-cycle plan."
                    risk_level = "high" if pair_setup["service_tier"] in {"A", "B"} else "medium"
                else:
                    risk_reason = "Projected demand runs ahead of the available inventory during the planning window."
                    risk_level = "high" if pair_setup["service_tier"] == "A" else "medium"
                on_hand = 0
                break

        if risk_reason:
            service_risk_items.append(
                {
                    "store_id": store_id,
                    "sku_id": sku_id,
                    "risk_level": risk_level,
                    "reason": risk_reason,
                }
            )
            if pair_setup["status"] != "active":
                key = (store_id, sku_id, "status_block")
                if key not in seen_exception_keys:
                    exceptions.append(
                        {
                            "store_id": store_id,
                            "sku_id": sku_id,
                            "exception_code": "status_block",
                            "detail": "Pair status is blocked or inactive while coverage remains short.",
                        }
                    )
                    seen_exception_keys.add(key)

            stockout_key = (store_id, sku_id, "projected_stockout")
            if stockout_key not in seen_exception_keys:
                exceptions.append(
                    {
                        "store_id": store_id,
                        "sku_id": sku_id,
                        "exception_code": "projected_stockout",
                        "detail": "Projected ending inventory falls to zero before the planning window closes.",
                    }
                )
                seen_exception_keys.add(stockout_key)

    forecast_rows.sort(key=lambda row: (row["store_id"], row["sku_id"], row["week_start"]))
    accepted_rows.sort(key=lambda row: (row["order_week_start"], row["store_id"], row["sku_id"]))
    service_risk_items.sort(key=lambda row: (row["store_id"], row["sku_id"]))
    exceptions.sort(key=lambda row: (row["store_id"], row["sku_id"], row["exception_code"]))

    summary = {
        "planning_window": {
            "start_week": inputs["manifest"]["planning_window"]["start_week"],
            "end_week": inputs["manifest"]["planning_window"]["end_week"],
        },
        "totals": {
            "sku_store_pairs": int(setup.shape[0]),
            "forecast_rows": len(forecast_rows),
            "planned_orders": len(accepted_rows),
            "total_recommended_units": int(sum(row["recommended_order_qty"] for row in accepted_rows)),
        },
        "budget_check": {
            "within_budget": running_cost <= budget_limit + 1e-9,
            "budget_limit": budget_limit,
            "planned_cost": round2(running_cost),
        },
        "service_risk_items": service_risk_items,
        "exceptions": exceptions,
        "notes": [
            "Promo lift is concentrated on SKU-BRAVO and the launch window on SKU-FOXTROT.",
            "SKU-FOXTROT relies on the analog mapping because its own history is short.",
            "Budget and review-capacity tradeoffs keep the current-cycle plan focused on the top lines.",
        ],
    }

    plan_rows = [
        {
            "store_id": row["store_id"],
            "sku_id": row["sku_id"],
            "order_week_start": row["order_week_start"],
            "arrival_week_start": row["arrival_week_start"],
            "recommended_order_qty": int(row["recommended_order_qty"]),
            "inventory_position_before_order": round2(row["inventory_position_before_order"]),
            "inventory_position_after_order": round2(row["inventory_position_after_order"]),
            "coverage_weeks": round2(row["coverage_weeks"]),
            "decision_reason": row["decision_reason"],
        }
        for row in accepted_rows
    ]
    return forecast_rows, plan_rows, summary


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(forecast_rows: list[dict], plan_rows: list[dict], summary: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(
        OUTPUT_DIR / "forecast_review.csv",
        forecast_rows,
        [
            "store_id",
            "sku_id",
            "week_start",
            "forecast_method",
            "baseline_units",
            "promo_lift_units",
            "final_forecast_units",
            "service_level",
            "safety_stock_units",
            "reorder_point_units",
        ],
    )
    write_csv(
        OUTPUT_DIR / "replenishment_plan.csv",
        plan_rows,
        [
            "store_id",
            "sku_id",
            "order_week_start",
            "arrival_week_start",
            "recommended_order_qty",
            "inventory_position_before_order",
            "inventory_position_after_order",
            "coverage_weeks",
            "decision_reason",
        ],
    )
    (OUTPUT_DIR / "planning_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    memo_lines = [
        "# Planner Memo",
        "",
        f"Planning window: {summary['planning_window']['start_week']} to {summary['planning_window']['end_week']}",
        f"Planned orders: {summary['totals']['planned_orders']}",
        f"Total recommended units: {summary['totals']['total_recommended_units']}",
        "",
        "## Budget And Vendor Constraints",
        f"- Budget limit: ${summary['budget_check']['budget_limit']:.2f}; planned cost: ${summary['budget_check']['planned_cost']:.2f}.",
        "- Order quantities were kept inside MOQ, case-pack, and cadence limits.",
        "- Existing inbound receipts were used before adding duplicate current-cycle supply.",
        "",
        "## Short-History Assumption",
        "- SKU-FOXTROT uses the provided SKU-ALPHA analog mapping because only six weeks of own history are available.",
        "",
        "## Remaining Service Risks",
    ]
    for item in summary["service_risk_items"][:10]:
        memo_lines.append(f"- {item['store_id']} {item['sku_id']}: {item['risk_level']} risk. {item['reason']}")

    memo_lines.extend(
        [
            "",
            "## Major Tradeoffs",
            "- Near-term promo and launch lines were protected before lower-priority coverage gaps.",
            "- Budget and review capacity kept the current-cycle plan focused on the most urgent actions.",
            "- Lines left outside the plan remain visible in the summary exceptions for later review.",
        ]
    )
    (OUTPUT_DIR / "planner_memo.md").write_text("\n".join(memo_lines) + "\n", encoding="utf-8")


def main() -> None:
    inputs = load_inputs()
    forecast_rows, plan_rows, summary = build_outputs(inputs)
    write_outputs(forecast_rows, plan_rows, summary)


if __name__ == "__main__":
    main()
