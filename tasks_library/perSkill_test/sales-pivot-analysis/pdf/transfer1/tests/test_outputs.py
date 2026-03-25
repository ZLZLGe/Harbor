#!/usr/bin/env python3
import csv
import json
from collections import defaultdict
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer1_store_kpi_rollup.csv")
SOURCE_PATH = Path("/tests/fixtures/source.json")
HEADERS = [
    "region",
    "total_orders",
    "total_revenue",
    "total_returns",
    "return_rate_pct",
    "revenue_per_labor_hour",
]


def build_expected():
    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    totals = defaultdict(lambda: {"orders": 0, "revenue": 0, "returns": 0, "labor_hours": 0})
    for row in rows:
        region = row["region"]
        totals[region]["orders"] += row["orders"]
        totals[region]["revenue"] += row["revenue"]
        totals[region]["returns"] += row["returns"]
        totals[region]["labor_hours"] += row["labor_hours"]

    expected = []
    for region in sorted(totals):
        summary = totals[region]
        expected.append(
            {
                "region": region,
                "total_orders": str(summary["orders"]),
                "total_revenue": str(summary["revenue"]),
                "total_returns": str(summary["returns"]),
                "return_rate_pct": f"{round(summary['returns'] / summary['orders'] * 100, 2):.2f}",
                "revenue_per_labor_hour": f"{round(summary['revenue'] / summary['labor_hours'], 2):.2f}",
            }
        )
    return expected


def main():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == HEADERS, f"unexpected headers: {reader.fieldnames}"
        actual = list(reader)
    expected = build_expected()
    assert actual == expected, "store KPI rollup CSV does not match expected output"


if __name__ == "__main__":
    main()
