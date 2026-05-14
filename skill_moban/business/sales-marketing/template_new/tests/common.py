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

FORECAST_PATH = OUTPUT_DIR / "forecast_review.csv"
PLAN_PATH = OUTPUT_DIR / "replenishment_plan.csv"
SUMMARY_PATH = OUTPUT_DIR / "planning_summary.json"
MEMO_PATH = OUTPUT_DIR / "planner_memo.md"

MANIFEST_PATH = DATA_ROOT / "planning_manifest.json"
POLICY_PATH = DATA_ROOT / "planning_policy.yaml"
HISTORY_PATH = DATA_ROOT / "historical_demand_weekly.csv"
SETUP_PATH = DATA_ROOT / "sku_store_setup.csv"
INVENTORY_PATH = DATA_ROOT / "inventory_snapshot.csv"
OPEN_PO_PATH = DATA_ROOT / "open_purchase_orders.csv"
PROMO_PATH = DATA_ROOT / "promotion_schedule.csv"
VENDOR_PATH = DATA_ROOT / "vendor_constraints.csv"
ANALOG_PATH = DATA_ROOT / "new_sku_analogs.csv"

FORECAST_FIELDS = [
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
]

PLAN_FIELDS = [
    "store_id",
    "sku_id",
    "order_week_start",
    "arrival_week_start",
    "recommended_order_qty",
    "inventory_position_before_order",
    "inventory_position_after_order",
    "coverage_weeks",
    "decision_reason",
]

TIER_RANK = {"A": 0, "B": 1, "C": 2}


def round2(value: float) -> float:
    return round(float(value), 2)


def ceil_int(value: float) -> int:
    return int(math.ceil(float(value)))


def parse_float(value: object) -> float:
    return round(float(value), 2)


def parse_int(value: object) -> int:
    return int(round(float(value)))


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def load_inputs() -> dict:
    history = pd.read_csv(HISTORY_PATH)
    history["week_start"] = pd.to_datetime(history["week_start"])

    setup = pd.read_csv(SETUP_PATH)
    inventory = pd.read_csv(INVENTORY_PATH)

    open_po = pd.read_csv(OPEN_PO_PATH)
    if not open_po.empty:
        open_po["arrival_week_start"] = pd.to_datetime(open_po["arrival_week_start"])

    promo = pd.read_csv(PROMO_PATH)
    promo["week_start"] = pd.to_datetime(promo["week_start"])

    vendor = pd.read_csv(VENDOR_PATH)
    analogs = pd.read_csv(ANALOG_PATH)

    manifest = load_manifest()
    policy = load_policy()
    plan_weeks = [pd.Timestamp(value) for value in manifest["planning_window"]["week_starts"]]

    return {
        "history": history,
        "setup": setup,
        "inventory": inventory,
        "open_po": open_po,
        "promo": promo,
        "vendor": vendor,
        "analogs": analogs,
        "manifest": manifest,
        "policy": policy,
        "plan_weeks": plan_weeks,
    }


def load_forecast_rows() -> list[dict]:
    with FORECAST_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_plan_rows() -> list[dict]:
    with PLAN_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def forecast_lookup(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    return {(row["store_id"], row["sku_id"], row["week_start"]): row for row in rows}


def setup_lookup(inputs: dict) -> dict[tuple[str, str], dict]:
    return {
        (row["store_id"], row["sku_id"]): row.to_dict()
        for _, row in inputs["setup"].iterrows()
    }


def vendor_lookup(inputs: dict) -> dict[str, dict]:
    return {row["sku_id"]: row.to_dict() for _, row in inputs["vendor"].iterrows()}


def analog_lookup(inputs: dict) -> dict[tuple[str, str], dict]:
    return {
        (row["store_id"], row["sku_id"]): row.to_dict()
        for _, row in inputs["analogs"].iterrows()
    }


def promo_lookup(inputs: dict) -> dict[tuple[str, str, pd.Timestamp], float]:
    return {
        (row["store_id"], row["sku_id"], row["week_start"]): float(row["demand_multiplier"])
        for _, row in inputs["promo"].iterrows()
    }


def profile_method_map(inputs: dict) -> dict[str, str]:
    policy = inputs["policy"]
    return {
        "stable": policy["forecast_rules"]["stable"]["method"],
        "trend": policy["forecast_rules"]["trend"]["method"],
        "intermittent": policy["forecast_rules"]["intermittent"]["method"],
        "launch": policy["forecast_rules"]["launch"]["method"],
    }


def build_reference_forecast() -> list[dict]:
    inputs = load_inputs()
    history = inputs["history"]
    setup = inputs["setup"]
    vendor_by_sku = vendor_lookup(inputs)
    analog_by_pair = analog_lookup(inputs)
    promo_map = promo_lookup(inputs)
    policy = inputs["policy"]
    plan_weeks = inputs["plan_weeks"]

    rows: list[dict] = []
    for _, pair in setup.sort_values(["store_id", "sku_id"]).iterrows():
        store_id = pair["store_id"]
        sku_id = pair["sku_id"]
        profile = pair["demand_profile"]
        tier = pair["service_tier"]
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

        baseline = round2(baseline)
        sigma = float(0.0 if pd.isna(sigma) else sigma)
        lead_time = int(vendor_by_sku[sku_id]["lead_time_weeks"])
        service_level = float(policy["service_level_output"][tier])
        safety_stock = ceil_int(
            policy["service_level_z"][tier]
            * sigma
            * math.sqrt(lead_time + int(policy["review_period_weeks"]))
            * float(policy["profile_sigma_multiplier"][profile])
        )

        pair_rows = []
        for idx, week_start in enumerate(plan_weeks):
            multiplier = float(promo_map.get((store_id, sku_id, week_start), 1.0))
            final_forecast = round2(baseline * multiplier)
            lead_cover = sum(
                round2(
                    baseline
                    * float(
                        promo_map.get((store_id, sku_id, future_week), 1.0)
                    )
                )
                for future_week in plan_weeks[idx : idx + lead_time]
            )
            pair_rows.append(
                {
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
            )
        rows.extend(pair_rows)

    return sorted(rows, key=lambda row: (row["store_id"], row["sku_id"], row["week_start"]))


def build_reference_lookup() -> dict[tuple[str, str, str], dict]:
    return forecast_lookup(build_reference_forecast())


def compute_plan_cost(plan_rows: list[dict], inputs: dict) -> float:
    vendor_by_sku = vendor_lookup(inputs)
    total = 0.0
    for row in plan_rows:
        total += parse_int(row["recommended_order_qty"]) * float(vendor_by_sku[row["sku_id"]]["unit_cost"])
    return round2(total)


def active_foxtrot_pairs(inputs: dict) -> set[tuple[str, str]]:
    setup = inputs["setup"]
    return {
        (row["store_id"], row["sku_id"])
        for _, row in setup.iterrows()
        if row["sku_id"] == "SKU-FOXTROT" and row["status"] == "active"
    }


def promo_window_pairs(inputs: dict) -> set[tuple[str, str]]:
    promo = inputs["promo"]
    plan_weeks = inputs["plan_weeks"]
    promo_window = set(plan_weeks[:3])
    return {
        (row["store_id"], row["sku_id"])
        for _, row in promo.iterrows()
        if row["week_start"] in promo_window
    }
