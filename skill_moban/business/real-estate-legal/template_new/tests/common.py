from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path

import pandas as pd
import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))

FACTS_PATH = OUTPUT_ROOT / "fundraising_facts.json"
MODEL_PATH = OUTPUT_ROOT / "financial_model.csv"
FUNDS_PATH = OUTPUT_ROOT / "use_of_funds.csv"
RECON_PATH = OUTPUT_ROOT / "reconciliation_log.csv"
MEMO_PATH = OUTPUT_ROOT / "investor_memo.md"
ONE_PAGER_PATH = OUTPUT_ROOT / "one_pager.md"

FACTS_MARKET_FIELDS = [
    "metro",
    "renter_households",
    "renter_share_pct",
    "median_rent_burden_pct",
    "median_gross_rent_usd",
    "median_household_income_usd",
]
MODEL_FIELDS = [
    "quarter",
    "beginning_cash_usd",
    "new_property_manager_customers",
    "new_law_firm_customers",
    "ending_property_manager_customers",
    "ending_law_firm_customers",
    "subscription_revenue_usd",
    "implementation_revenue_usd",
    "total_revenue_usd",
    "people_cost_usd",
    "go_to_market_cost_usd",
    "other_opex_usd",
    "net_burn_usd",
    "ending_cash_usd",
]
FUNDS_FIELDS = ["category", "amount_usd", "share_of_raise", "notes"]
RECON_FIELDS = ["field_id", "current_value", "conflicting_value", "conflict_source", "resolution_reason"]


def load_round_brief() -> dict:
    return json.loads((DATA_ROOT / "round_brief.json").read_text(encoding="utf-8"))


def load_policy() -> dict:
    return yaml.safe_load((DATA_ROOT / "delivery_policy.yaml").read_text(encoding="utf-8"))


def load_pricing_traction() -> dict:
    return yaml.safe_load((DATA_ROOT / "company_notes/pricing_and_traction.yaml").read_text(encoding="utf-8"))


def load_market_snapshot() -> pd.DataFrame:
    return pd.read_csv(DATA_ROOT / "market_snapshots/metro_housing_snapshot.csv")


def load_assumptions() -> pd.DataFrame:
    return pd.read_csv(DATA_ROOT / "company_notes/base_case_assumptions.csv")


def load_milestones() -> list[dict]:
    with (DATA_ROOT / "company_notes/milestones.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def expected_facts() -> dict:
    brief = load_round_brief()
    pricing_traction = load_pricing_traction()
    market = load_market_snapshot()
    milestones = load_milestones()

    markets = []
    for metro in brief["approved_metros"]:
        row = market.loc[market["metro"] == metro].iloc[0]
        markets.append({
            "metro": metro,
            "renter_households": int(row["renter_households"]),
            "renter_share_pct": float(row["renter_households"] / row["total_households"]),
            "median_rent_burden_pct": float(row["median_rent_burden_pct"] / 100.0),
            "median_gross_rent_usd": int(row["median_gross_rent_usd"]),
            "median_household_income_usd": int(row["median_household_income_usd"]),
        })

    return {
        "company_name": brief["company_name"],
        "round": brief["round"],
        "pricing": pricing_traction["pricing"],
        "traction": pricing_traction["traction"],
        "markets": markets,
        "milestones": milestones,
    }


def expected_model_rows() -> list[dict]:
    brief = load_round_brief()
    policy = load_policy()
    pricing_traction = load_pricing_traction()
    assumptions = load_assumptions()

    scenario = policy["approved_scenario"]
    base = assumptions.loc[assumptions["scenario"] == scenario].copy()
    base = base.reset_index(drop=True)

    pm_monthly = int(pricing_traction["pricing"]["property_manager"]["monthly_subscription_usd"])
    lf_monthly = int(pricing_traction["pricing"]["law_firm"]["monthly_subscription_usd"])
    pm_impl = int(pricing_traction["pricing"]["property_manager"]["implementation_fee_usd"])
    lf_impl = int(pricing_traction["pricing"]["law_firm"]["implementation_fee_usd"])
    quarter_months = int(policy["financial_model_rules"]["quarter_months"])

    pm_customers = int(pricing_traction["traction"]["active_property_manager_customers"])
    lf_customers = int(pricing_traction["traction"]["active_law_firm_customers"])
    cash = int(brief["current_cash_usd"] + brief["round"]["target_raise_usd"])

    rows = []
    for _, row in base.iterrows():
        new_pm = int(row["new_property_manager_customers"])
        new_lf = int(row["new_law_firm_customers"])
        ending_pm = pm_customers + new_pm
        ending_lf = lf_customers + new_lf
        subscription = int(
            ((pm_customers + 0.5 * new_pm) * pm_monthly * quarter_months)
            + ((lf_customers + 0.5 * new_lf) * lf_monthly * quarter_months)
        )
        implementation = int((new_pm * pm_impl) + (new_lf * lf_impl))
        total = int(subscription + implementation)
        people = int(row["people_cost_usd"])
        gtm = int(row["go_to_market_cost_usd"])
        other = int(row["other_opex_usd"])
        burn = int(people + gtm + other - total)
        ending_cash = int(cash - burn)
        rows.append({
            "quarter": row["quarter"],
            "beginning_cash_usd": cash,
            "new_property_manager_customers": new_pm,
            "new_law_firm_customers": new_lf,
            "ending_property_manager_customers": ending_pm,
            "ending_law_firm_customers": ending_lf,
            "subscription_revenue_usd": subscription,
            "implementation_revenue_usd": implementation,
            "total_revenue_usd": total,
            "people_cost_usd": people,
            "go_to_market_cost_usd": gtm,
            "other_opex_usd": other,
            "net_burn_usd": burn,
            "ending_cash_usd": ending_cash,
        })
        pm_customers = ending_pm
        lf_customers = ending_lf
        cash = ending_cash

    return rows


def expected_use_of_funds() -> list[dict]:
    brief = load_round_brief()
    policy = load_policy()
    target = int(brief["round"]["target_raise_usd"])
    rows = []
    running = 0
    for idx, item in enumerate(policy["use_of_funds"]):
        share = float(item["share_of_raise"])
        if idx < len(policy["use_of_funds"]) - 1:
            amount = int(round(target * share))
            running += amount
        else:
            amount = target - running
        rows.append({
            "category": item["category"],
            "amount_usd": amount,
            "share_of_raise": share,
            "notes": item["notes"],
        })
    return rows


def expected_reconciliation_rows() -> list[dict]:
    return [
        {"field_id": "target_raise_usd", "current_value": "2250000", "conflicting_value": "2500000", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_round_brief"},
        {"field_id": "minimum_raise_usd", "current_value": "1500000", "conflicting_value": "1250000", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_round_brief"},
        {"field_id": "instrument", "current_value": "post-money SAFE", "conflicting_value": "priced_seed", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_round_brief"},
        {"field_id": "property_manager_monthly_subscription_usd", "current_value": "1290", "conflicting_value": "1190", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_pricing"},
        {"field_id": "law_firm_monthly_subscription_usd", "current_value": "1890", "conflicting_value": "1790", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_pricing"},
        {"field_id": "annualized_platform_revenue_usd", "current_value": "482760", "conflicting_value": "455880", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_traction"},
        {"field_id": "pilot_conversion_rate", "current_value": "0.58", "conflicting_value": "0.52", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_traction"},
        {"field_id": "gross_revenue_retention", "current_value": "0.93", "conflicting_value": "0.89", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_traction"},
        {"field_id": "third_metro", "current_value": "Phoenix", "conflicting_value": "Tampa", "conflict_source": "draft_materials/legacy_metrics.csv", "resolution_reason": "current_metro_scope"},
        {"field_id": "target_raise_usd", "current_value": "2250000", "conflicting_value": "2500000", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_round_brief"},
        {"field_id": "instrument", "current_value": "post-money SAFE", "conflicting_value": "priced seed", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_round_brief"},
        {"field_id": "property_manager_monthly_subscription_usd", "current_value": "1290", "conflicting_value": "1190", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_pricing"},
        {"field_id": "law_firm_monthly_subscription_usd", "current_value": "1890", "conflicting_value": "1790", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_pricing"},
        {"field_id": "active_property_manager_customers", "current_value": "18", "conflicting_value": "16", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_traction"},
        {"field_id": "active_law_firm_customers", "current_value": "9", "conflicting_value": "7", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_traction"},
        {"field_id": "annualized_platform_revenue_usd", "current_value": "482760", "conflicting_value": "455880", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_traction"},
        {"field_id": "third_metro", "current_value": "Phoenix", "conflicting_value": "Tampa", "conflict_source": "draft_materials/investor_memo_old.md", "resolution_reason": "current_metro_scope"},
        {"field_id": "target_raise_usd", "current_value": "2250000", "conflicting_value": "2000000", "conflict_source": "draft_materials/one_pager_old.md", "resolution_reason": "current_round_brief"},
        {"field_id": "instrument", "current_value": "post-money SAFE", "conflicting_value": "convertible note", "conflict_source": "draft_materials/one_pager_old.md", "resolution_reason": "current_round_brief"},
        {"field_id": "annualized_platform_revenue_usd", "current_value": "482760", "conflicting_value": "438000", "conflict_source": "draft_materials/one_pager_old.md", "resolution_reason": "current_traction"},
        {"field_id": "pm_customer_milestone_2027_q4", "current_value": "milestone_target=50", "conflicting_value": "base_case_model_ending_pm_customers=45", "conflict_source": "current_inputs", "resolution_reason": "risk_callout_required"},
    ]


def normalize_reconciliation_row(row: dict) -> dict:
    normalized = dict(row)
    normalized["conflicting_value"] = normalized["conflicting_value"].replace("_", " ")

    if (
        normalized["field_id"] == "pm_customer_milestone_2027_q4"
        and normalized["conflict_source"] == "current_inputs"
    ):
        current_value = normalized["current_value"].strip().lower()
        conflicting_value = normalized["conflicting_value"].strip().lower()

        if current_value in {
            "milestone_target=50",
            "approved_milestone=50",
            "reach fifty active property manager customers",
            "50",
        }:
            normalized["current_value"] = "milestone_target=50"

        if conflicting_value in {
            "base case model ending pm customers=45",
            "base case ending property manager customers=45",
            "base model ending property manager customers=45",
            "45",
        }:
            normalized["conflicting_value"] = "base_case_model_ending_pm_customers=45"

    return normalized


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assert_close(actual: float, expected: float, field: str, tol: float = 1e-4) -> None:
    assert math.isclose(actual, expected, rel_tol=tol, abs_tol=tol), f"{field} mismatch: {actual} != {expected}"


def money_variants(value: int) -> list[str]:
    millions = value / 1_000_000
    return [
        f"${value:,}",
        f"${value}",
        f"{millions:.2f}M",
        f"{millions:.2f}m",
    ]


def text_has_any(text: str, options: list[str]) -> bool:
    lowered = text.lower()
    return any(option.lower() in lowered for option in options)


def assert_contains_money(text: str, value: int, label: str) -> None:
    assert text_has_any(text, money_variants(value)), f"{label} is missing from text"


def assert_heading_once(text: str, heading: str) -> None:
    assert text.count(heading) == 1, f"Heading {heading} must appear exactly once"


def stale_markers() -> list[str]:
    return [
        "Tampa",
        "$2.5M",
        "$2.0M",
        "priced seed",
        "convertible note",
        "$1,190",
        "$1,790",
        "$455,880",
        "$438,000",
    ]
