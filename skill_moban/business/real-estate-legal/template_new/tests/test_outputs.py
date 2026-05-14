from __future__ import annotations

from common import (
    FACTS_MARKET_FIELDS,
    FACTS_PATH,
    FUNDS_FIELDS,
    FUNDS_PATH,
    MEMO_PATH,
    MODEL_FIELDS,
    MODEL_PATH,
    ONE_PAGER_PATH,
    RECON_FIELDS,
    RECON_PATH,
    assert_close,
    assert_contains_money,
    assert_heading_once,
    normalize_reconciliation_row,
    expected_facts,
    expected_model_rows,
    expected_reconciliation_rows,
    expected_use_of_funds,
    load_csv_rows,
    load_json,
)


def test_required_output_files_exist() -> None:
    assert FACTS_PATH.exists(), "Missing /root/output/fundraising_facts.json"
    assert MODEL_PATH.exists(), "Missing /root/output/financial_model.csv"
    assert FUNDS_PATH.exists(), "Missing /root/output/use_of_funds.csv"
    assert RECON_PATH.exists(), "Missing /root/output/reconciliation_log.csv"
    assert MEMO_PATH.exists(), "Missing /root/output/investor_memo.md"
    assert ONE_PAGER_PATH.exists(), "Missing /root/output/one_pager.md"


def test_fundraising_facts_match_expected_values() -> None:
    actual = load_json(FACTS_PATH)
    expected = expected_facts()

    assert actual["company_name"] == expected["company_name"]
    assert actual["round"] == expected["round"]
    assert actual["pricing"] == expected["pricing"]
    assert actual["traction"] == expected["traction"]
    assert len(actual["markets"]) == len(expected["markets"])
    for actual_market, expected_market in zip(actual["markets"], expected["markets"]):
        assert list(actual_market.keys()) == FACTS_MARKET_FIELDS
        assert actual_market["metro"] == expected_market["metro"]
        assert int(actual_market["renter_households"]) == expected_market["renter_households"]
        assert int(actual_market["median_gross_rent_usd"]) == expected_market["median_gross_rent_usd"]
        assert int(actual_market["median_household_income_usd"]) == expected_market["median_household_income_usd"]
        assert_close(float(actual_market["renter_share_pct"]), expected_market["renter_share_pct"], f"{expected_market['metro']} renter_share_pct")
        assert_close(float(actual_market["median_rent_burden_pct"]), expected_market["median_rent_burden_pct"], f"{expected_market['metro']} median_rent_burden_pct")

    assert actual["milestones"] == expected["milestones"]


def test_financial_model_matches_expected_rollforward() -> None:
    rows = load_csv_rows(MODEL_PATH)
    expected_rows = expected_model_rows()

    assert len(rows) == len(expected_rows), "Unexpected number of model rows"
    for actual_row, expected_row in zip(rows, expected_rows):
        assert list(actual_row.keys()) == MODEL_FIELDS
        for field in MODEL_FIELDS:
            if field == "quarter":
                assert actual_row[field] == expected_row[field], f"{field} mismatch"
            else:
                assert int(actual_row[field]) == expected_row[field], f"{field} mismatch in {expected_row['quarter']}"


def test_use_of_funds_matches_policy() -> None:
    rows = load_csv_rows(FUNDS_PATH)
    expected_rows = expected_use_of_funds()

    assert len(rows) == len(expected_rows), "Unexpected number of use-of-funds rows"
    amount_total = 0
    share_total = 0.0
    for actual_row, expected_row in zip(rows, expected_rows):
        assert list(actual_row.keys()) == FUNDS_FIELDS
        assert actual_row["category"] == expected_row["category"]
        assert int(actual_row["amount_usd"]) == expected_row["amount_usd"]
        assert_close(float(actual_row["share_of_raise"]), expected_row["share_of_raise"], f"share_of_raise for {expected_row['category']}")
        assert actual_row["notes"] == expected_row["notes"]
        amount_total += int(actual_row["amount_usd"])
        share_total += float(actual_row["share_of_raise"])

    assert amount_total == sum(row["amount_usd"] for row in expected_rows)
    assert_close(share_total, 1.0, "share_of_raise total")


def test_reconciliation_log_covers_conflicts_and_tension() -> None:
    rows = load_csv_rows(RECON_PATH)
    expected_rows = expected_reconciliation_rows()
    assert len(rows) == len(expected_rows), "Unexpected number of reconciliation rows"
    normalized_actual = []
    for actual_row in rows:
        assert list(actual_row.keys()) == RECON_FIELDS
        normalized_actual.append(normalize_reconciliation_row(actual_row))

    normalized_expected = [normalize_reconciliation_row(expected_row) for expected_row in expected_rows]

    def reconciliation_sort_key(row: dict) -> tuple[str, str, str, str, str]:
        return (
            row["field_id"],
            row["conflict_source"],
            row["current_value"],
            row["conflicting_value"],
            row["resolution_reason"],
        )

    assert sorted(normalized_actual, key=reconciliation_sort_key) == sorted(
        normalized_expected,
        key=reconciliation_sort_key,
    )


def test_investor_memo_contains_current_facts() -> None:
    facts = expected_facts()
    text = MEMO_PATH.read_text(encoding="utf-8")

    assert text.startswith("# NoticeFlow Investor Memo")
    for heading in [
        "## Company",
        "## Problem",
        "## Product",
        "## Market",
        "## Business Model",
        "## Traction",
        "## Raise",
        "## Use of Funds",
        "## Risks",
        "## Milestones",
    ]:
        assert_heading_once(text, heading)

    for metro in ["Atlanta", "Dallas", "Phoenix"]:
        assert metro in text, f"Memo missing metro {metro}"

    assert "post-money SAFE" in text
    assert_contains_money(text, int(facts["round"]["target_raise_usd"]), "target raise")
    assert_contains_money(text, int(facts["pricing"]["property_manager"]["monthly_subscription_usd"]), "property manager pricing")
    assert_contains_money(text, int(facts["pricing"]["law_firm"]["monthly_subscription_usd"]), "law firm pricing")
    assert_contains_money(text, int(facts["traction"]["annualized_platform_revenue_usd"]), "annualized revenue")
    assert "45" in text and "50" in text, "Memo must mention the 2027-Q4 milestone-versus-model risk"



def test_one_pager_contains_current_facts() -> None:
    facts = expected_facts()
    text = ONE_PAGER_PATH.read_text(encoding="utf-8")

    assert text.startswith("# NoticeFlow")
    for heading in [
        "## What We Do",
        "## Why Now",
        "## Market Snapshot",
        "## Traction",
        "## Raise Summary",
    ]:
        assert_heading_once(text, heading)

    for metro in ["Atlanta", "Dallas", "Phoenix"]:
        assert metro in text, f"One-pager missing metro {metro}"

    assert "post-money SAFE" in text
    assert_contains_money(text, int(facts["round"]["target_raise_usd"]), "target raise")
    assert_contains_money(text, int(facts["traction"]["annualized_platform_revenue_usd"]), "annualized revenue")
