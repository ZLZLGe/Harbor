from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pandas as pd
import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    brief = json.loads((DATA_ROOT / "round_brief.json").read_text(encoding="utf-8"))
    policy = yaml.safe_load((DATA_ROOT / "delivery_policy.yaml").read_text(encoding="utf-8"))
    pricing_traction = yaml.safe_load((DATA_ROOT / "company_notes/pricing_and_traction.yaml").read_text(encoding="utf-8"))
    market = pd.read_csv(DATA_ROOT / "market_snapshots/metro_housing_snapshot.csv")
    assumptions = pd.read_csv(DATA_ROOT / "company_notes/base_case_assumptions.csv")
    milestones = list(csv.DictReader((DATA_ROOT / "company_notes/milestones.csv").open("r", encoding="utf-8", newline="")))

    facts = build_facts(brief, pricing_traction, market, milestones)
    model_rows = build_model(brief, policy, pricing_traction, assumptions)
    funds_rows = build_funds(brief, policy)
    recon_rows = build_reconciliation_rows()

    (OUTPUT_ROOT / "fundraising_facts.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
    write_csv(OUTPUT_ROOT / "financial_model.csv", model_rows)
    write_csv(OUTPUT_ROOT / "use_of_funds.csv", funds_rows)
    write_csv(OUTPUT_ROOT / "reconciliation_log.csv", recon_rows)
    (OUTPUT_ROOT / "investor_memo.md").write_text(build_memo(facts, funds_rows), encoding="utf-8")
    (OUTPUT_ROOT / "one_pager.md").write_text(build_one_pager(facts), encoding="utf-8")


def build_facts(brief: dict, pricing_traction: dict, market: pd.DataFrame, milestones: list[dict]) -> dict:
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


def build_model(brief: dict, policy: dict, pricing_traction: dict, assumptions: pd.DataFrame) -> list[dict]:
    base = assumptions.loc[assumptions["scenario"] == policy["approved_scenario"]].reset_index(drop=True)
    quarter_months = int(policy["financial_model_rules"]["quarter_months"])
    pm_monthly = int(pricing_traction["pricing"]["property_manager"]["monthly_subscription_usd"])
    lf_monthly = int(pricing_traction["pricing"]["law_firm"]["monthly_subscription_usd"])
    pm_impl = int(pricing_traction["pricing"]["property_manager"]["implementation_fee_usd"])
    lf_impl = int(pricing_traction["pricing"]["law_firm"]["implementation_fee_usd"])
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


def build_funds(brief: dict, policy: dict) -> list[dict]:
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


def build_reconciliation_rows() -> list[dict]:
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


def build_memo(facts: dict, funds_rows: list[dict]) -> str:
    metros = ", ".join(market["metro"] for market in facts["markets"])
    market_lines = "\n".join(
        f"- {market['metro']}: {market['renter_households']:,} renter households, {market['renter_share_pct']:.1%} renter share, "
        f"${market['median_gross_rent_usd']:,} median gross rent, and {market['median_rent_burden_pct']:.1%} median rent burden."
        for market in facts["markets"]
    )
    fund_lines = "\n".join(
        f"- {row['category']}: ${row['amount_usd']:,} ({row['share_of_raise']:.0%}) for {row['notes'].rstrip('.')}"
        for row in funds_rows
    )
    milestone_lines = "\n".join(
        f"- {item['quarter']}: {item['milestone']} ({item['owner']})"
        for item in facts["milestones"]
    )
    return (
        "# NoticeFlow Investor Memo\n\n"
        "## Company\n"
        "NoticeFlow is workflow software for property managers and housing-focused law firms handling recurring rental notice and filing preparation work.\n\n"
        "## Problem\n"
        "Landlord-tenant matters still move across email, spreadsheets, call notes, and outside counsel handoffs, which creates missed steps and slow document preparation.\n\n"
        "## Product\n"
        "NoticeFlow combines notice tracking, intake, customer communication, and court packet preparation in one workspace for operations teams and counsel.\n\n"
        "## Market\n"
        f"NoticeFlow is currently focused on {metros}.\n"
        f"{market_lines}\n\n"
        "## Business Model\n"
        f"Property manager customers pay ${facts['pricing']['property_manager']['monthly_subscription_usd']:,} per month plus a ${facts['pricing']['property_manager']['implementation_fee_usd']:,} implementation fee. "
        f"Law firm customers pay ${facts['pricing']['law_firm']['monthly_subscription_usd']:,} per month plus a ${facts['pricing']['law_firm']['implementation_fee_usd']:,} implementation fee.\n\n"
        "## Traction\n"
        f"NoticeFlow serves {facts['traction']['active_property_manager_customers']} property manager customers and {facts['traction']['active_law_firm_customers']} housing-focused law firm customers. "
        f"Annualized platform revenue is ${facts['traction']['annualized_platform_revenue_usd']:,}, with {facts['traction']['pilot_conversion_rate']:.0%} pilot conversion and {facts['traction']['gross_revenue_retention']:.0%} gross revenue retention.\n\n"
        "## Raise\n"
        f"NoticeFlow is raising ${facts['round']['target_raise_usd']:,} on a {facts['round']['instrument']} with a ${facts['round']['minimum_raise_usd']:,} minimum and a target close in {facts['round']['close_target_quarter']}.\n\n"
        "## Use of Funds\n"
        f"{fund_lines}\n\n"
        "## Risks\n"
        "The approved base-case model reaches 45 active property manager customers in 2027-Q4, while the approved milestone plan targets 50 in the same quarter. That gap makes 2027-Q4 customer acquisition the key execution risk to monitor.\n\n"
        "## Milestones\n"
        f"{milestone_lines}\n"
    )


def build_one_pager(facts: dict) -> str:
    metros = ", ".join(market["metro"] for market in facts["markets"])
    return (
        "# NoticeFlow\n\n"
        "## What We Do\n"
        "NoticeFlow helps property managers and housing-focused law firms coordinate notices, tenant communication, intake, and filing prep in one workflow.\n\n"
        "## Why Now\n"
        "Rental operations teams want faster notice handling, cleaner handoffs to counsel, and better process coverage as multistate volume grows.\n\n"
        "## Market Snapshot\n"
        f"Current focus metros are {metros}. Atlanta has {facts['markets'][0]['renter_households']:,} renter households, Dallas has {facts['markets'][1]['renter_households']:,}, and Phoenix has {facts['markets'][2]['renter_households']:,}. "
        f"Median gross rent ranges from ${min(m['median_gross_rent_usd'] for m in facts['markets']):,} to ${max(m['median_gross_rent_usd'] for m in facts['markets']):,} across the current footprint.\n\n"
        "## Traction\n"
        f"NoticeFlow has {facts['traction']['active_property_manager_customers']} property manager customers, {facts['traction']['active_law_firm_customers']} law firm customers, and ${facts['traction']['annualized_platform_revenue_usd']:,} in annualized platform revenue.\n\n"
        "## Raise Summary\n"
        f"NoticeFlow is raising ${facts['round']['target_raise_usd']:,} on a {facts['round']['instrument']} to extend workflow coverage, implementation capacity, and metro go-to-market execution.\n"
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
