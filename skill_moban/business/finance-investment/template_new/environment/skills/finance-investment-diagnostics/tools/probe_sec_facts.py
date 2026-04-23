from __future__ import annotations

import csv
import json
from pathlib import Path


DATA_ROOT = Path("/app/data")
UNIVERSE = DATA_ROOT / "reference" / "company_universe.csv"
SEC_ROOT = DATA_ROOT / "sec_companyfacts"

CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditures": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalentsAndShortTermInvestments",
    ],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "shares": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "CommonStockSharesOutstanding",
    ],
    "eps": ["EarningsPerShareDiluted"],
}


def has_year(data: dict, concept: str, unit: str, year: int) -> bool:
    facts = data.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get(unit, [])
    return any(item.get("form") == "10-K" and item.get("fp") == "FY" and item.get("fy") == year for item in facts)


def first_concept(data: dict, concepts: list[str], unit: str, year: int) -> str | None:
    for concept in concepts:
        if has_year(data, concept, unit, year):
            return concept
    return None


def main() -> None:
    with UNIVERSE.open("r", encoding="utf-8", newline="") as handle:
        companies = list(csv.DictReader(handle))
    for company in companies:
        ticker = company["ticker"]
        data = json.loads((SEC_ROOT / f"{ticker}.json").read_text(encoding="utf-8"))
        years = set()
        for concept in data.get("facts", {}).get("us-gaap", {}).values():
            for unit_facts in concept.get("units", {}).values():
                for fact in unit_facts:
                    if fact.get("form") == "10-K" and fact.get("fp") == "FY" and isinstance(fact.get("fy"), int):
                        years.add(fact["fy"])
        print(f"\n{ticker}: latest candidate fiscal years {sorted(years)[-5:]}")
        for year in sorted(years)[-3:]:
            found = {}
            for key, concepts in CONCEPTS.items():
                unit = "shares" if key == "shares" else "USD/shares" if key == "eps" else "USD"
                found[key] = first_concept(data, concepts, unit, year)
            print(f"  {year}: {found}")


if __name__ == "__main__":
    main()
