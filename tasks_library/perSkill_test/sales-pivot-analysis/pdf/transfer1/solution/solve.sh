#!/bin/bash
set -euo pipefail

cat <<'PY' > /tmp/solve_transfer1.py
import csv
from collections import defaultdict

import pdfplumber


PDF_PATH = "/root/store_packet.pdf"
OUTPUT_PATH = "/root/transfer1_store_kpi_rollup.csv"


def parse_int(value):
    return int(str(value).replace(",", "").strip())


def load_rows():
    rows = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for raw_row in table:
                    if not raw_row or len(raw_row) < 6:
                        continue
                    if str(raw_row[0]).strip().lower() == "store id":
                        continue
                    store_id = str(raw_row[0]).strip()
                    if not store_id:
                        continue
                    rows.append(
                        {
                            "store_id": store_id,
                            "region": str(raw_row[1]).strip(),
                            "orders": parse_int(raw_row[2]),
                            "revenue": parse_int(raw_row[3]),
                            "returns": parse_int(raw_row[4]),
                            "labor_hours": parse_int(raw_row[5]),
                        }
                    )
    if not rows:
        raise RuntimeError("No store rows were extracted from the PDF")
    return rows


def build_rollup(rows):
    totals = defaultdict(lambda: {"orders": 0, "revenue": 0, "returns": 0, "labor_hours": 0})
    for row in rows:
        region = row["region"]
        totals[region]["orders"] += row["orders"]
        totals[region]["revenue"] += row["revenue"]
        totals[region]["returns"] += row["returns"]
        totals[region]["labor_hours"] += row["labor_hours"]

    output_rows = []
    for region in sorted(totals):
        summary = totals[region]
        return_rate = round(summary["returns"] / summary["orders"] * 100, 2)
        revenue_per_hour = round(summary["revenue"] / summary["labor_hours"], 2)
        output_rows.append(
            {
                "region": region,
                "total_orders": str(summary["orders"]),
                "total_revenue": str(summary["revenue"]),
                "total_returns": str(summary["returns"]),
                "return_rate_pct": f"{return_rate:.2f}",
                "revenue_per_labor_hour": f"{revenue_per_hour:.2f}",
            }
        )
    return output_rows


def main():
    rows = load_rows()
    output_rows = build_rollup(rows)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "region",
                "total_orders",
                "total_revenue",
                "total_returns",
                "return_rate_pct",
                "revenue_per_labor_hour",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_transfer1.py
