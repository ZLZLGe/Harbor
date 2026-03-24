#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import pandas as pd
import pdfplumber

INPUT_PDF = "/root/regional_sales_report_input"
OUTPUT_CSV = "/root/regional_sales_rollup.csv"

MONTH_TO_QUARTER = {
    "Jan": "Q1",
    "Feb": "Q1",
    "Mar": "Q1",
    "Apr": "Q2",
    "May": "Q2",
    "Jun": "Q2",
}

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}

rows = []
with pdfplumber.open(INPUT_PDF) as pdf:
    for page in pdf.pages:
        for table in page.extract_tables(TABLE_SETTINGS):
            if not table:
                continue
            header = [str(cell).strip() if cell else "" for cell in table[0]]
            start_idx = 1 if header[:5] == ["Region", "Month", "Gross Sales", "Refunds", "Net Sales"] else 0
            for raw_row in table[start_idx:]:
                if not raw_row or len(raw_row) < 5:
                    continue
                region, month, gross_sales, refunds, net_sales = [
                    str(cell).strip() if cell is not None else "" for cell in raw_row[:5]
                ]
                if not region or region == "Region" or month not in MONTH_TO_QUARTER:
                    continue
                rows.append(
                    {
                        "region": region,
                        "quarter": MONTH_TO_QUARTER[month],
                        "gross_sales": int(gross_sales.replace(",", "")),
                        "refunds": int(refunds.replace(",", "")),
                        "net_sales": int(net_sales.replace(",", "")),
                    }
                )

df = pd.DataFrame(rows)
result = (
    df.groupby(["region", "quarter"], as_index=False)[["gross_sales", "refunds", "net_sales"]]
    .sum()
    .sort_values(["region", "quarter"], kind="stable")
)
result.to_csv(OUTPUT_CSV, index=False)
PY
