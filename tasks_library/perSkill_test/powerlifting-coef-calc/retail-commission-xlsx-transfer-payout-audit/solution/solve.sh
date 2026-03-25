#!/bin/bash

set -euo pipefail

INPUT_FILE="/root/data/commission_source_template"
OUTPUT_FILE="/root/data/commission_payout_audit.xlsx"

cp "$INPUT_FILE" "$OUTPUT_FILE"

python3 - <<'PY'
from openpyxl import load_workbook

output_file = "/root/data/commission_payout_audit.xlsx"
wb = load_workbook(output_file)
orders_ws = wb["Orders"]
payouts_ws = wb["Payouts"]

headers = [
    "OrderID",
    "OrderDate",
    "Quarter",
    "RepID",
    "RepName",
    "Segment",
    "Amount",
    "BaseRate",
    "QuarterRepSales",
    "AcceleratorRate",
    "BaseCommission",
    "AcceleratorBonus",
    "FinalPayout",
    "AuditFlag",
]

for idx, header in enumerate(headers, start=1):
    payouts_ws.cell(row=1, column=idx, value=header)

last_row = orders_ws.max_row

for row_idx in range(2, last_row + 1):
    payouts_ws[f"A{row_idx}"] = f"=Orders!A{row_idx}"
    payouts_ws[f"B{row_idx}"] = f"=Orders!B{row_idx}"
    payouts_ws[f"C{row_idx}"] = f"=Orders!C{row_idx}"
    payouts_ws[f"D{row_idx}"] = f"=Orders!D{row_idx}"
    payouts_ws[f"E{row_idx}"] = f'=IFERROR(INDEX(RepRules!$B$2:$B$6,MATCH(D{row_idx},RepRules!$A$2:$A$6,0)),"")'
    payouts_ws[f"F{row_idx}"] = f"=Orders!E{row_idx}"
    payouts_ws[f"G{row_idx}"] = f"=Orders!F{row_idx}"
    payouts_ws[f"H{row_idx}"] = f'=IFERROR(INDEX(RepRules!$D$2:$D$6,MATCH(D{row_idx},RepRules!$A$2:$A$6,0)),"")'
    payouts_ws[f"I{row_idx}"] = f'=SUMIFS($G$2:$G${last_row},$C$2:$C${last_row},C{row_idx},$D$2:$D${last_row},D{row_idx})'
    payouts_ws[f"J{row_idx}"] = (
        f'=IF(COUNTIF(AcceleratorTiers!$A$2:$A$3,C{row_idx})=0,"",'
        f'IF(I{row_idx}>=INDEX(AcceleratorTiers!$D$2:$D$3,MATCH(C{row_idx},AcceleratorTiers!$A$2:$A$3,0)),'
        f'INDEX(AcceleratorTiers!$E$2:$E$3,MATCH(C{row_idx},AcceleratorTiers!$A$2:$A$3,0)),'
        f'IF(I{row_idx}>=INDEX(AcceleratorTiers!$B$2:$B$3,MATCH(C{row_idx},AcceleratorTiers!$A$2:$A$3,0)),'
        f'INDEX(AcceleratorTiers!$C$2:$C$3,MATCH(C{row_idx},AcceleratorTiers!$A$2:$A$3,0)),0)))'
    )
    payouts_ws[f"K{row_idx}"] = f'=IF(H{row_idx}="","",ROUND(G{row_idx}*H{row_idx},2))'
    payouts_ws[f"L{row_idx}"] = f'=IF(OR(H{row_idx}="",J{row_idx}=""),"",ROUND(G{row_idx}*J{row_idx},2))'
    payouts_ws[f"M{row_idx}"] = f'=IF(OR(K{row_idx}="",L{row_idx}=""),"",ROUND(K{row_idx}+L{row_idx},2))'
    payouts_ws[f"N{row_idx}"] = (
        f'=IF(E{row_idx}="","MISSING_REP_RULE",'
        f'IF(COUNTIF(AcceleratorTiers!$A$2:$A$3,C{row_idx})=0,"MISSING_ACCELERATOR_RULE","OK"))'
    )

wb.save(output_file)
PY

python3 /root/.codex/skills/xlsx/recalc.py "$OUTPUT_FILE" 60
