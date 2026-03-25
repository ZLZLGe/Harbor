#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import csv
from datetime import datetime

from openpyxl import load_workbook


TEMPLATE = "/root/bond-stress-template.xlsx"
OUTPUT = "/root/bond-stress-book.xlsx"
VALUATION_DATE = datetime(2026, 6, 30)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_headers_and_rows(ws, headers, rows):
    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=header)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, header in enumerate(headers, start=1):
            ws.cell(row=row_idx, column=col_idx, value=row[header])


holdings = read_csv("/root/portfolio_holdings.csv")
calendar_rows = read_csv("/root/coupon_calendar.csv")
curve_rows = read_csv("/root/risk_free_curve.csv")
recovery_rows = read_csv("/root/recovery_assumptions.csv")

wb = load_workbook(TEMPLATE)

control = wb["Control"]
control["B2"] = VALUATION_DATE

holdings_ws = wb["Holdings"]
holdings_headers = [
    "Bond_ID",
    "Issuer",
    "Rating_Bucket",
    "Coupon_Rate",
    "Position_Face",
    "Coupon_Frequency",
    "Curve_Tenor_Years",
    "Spread_Bps",
    "Stress_Default_Flag",
]
write_headers_and_rows(holdings_ws, holdings_headers, holdings)
for row_idx in range(2, len(holdings) + 2):
    holdings_ws[f"D{row_idx}"] = float(holdings_ws[f"D{row_idx}"].value)
    holdings_ws[f"E{row_idx}"] = float(holdings_ws[f"E{row_idx}"].value)
    holdings_ws[f"F{row_idx}"] = int(holdings_ws[f"F{row_idx}"].value)
    holdings_ws[f"G{row_idx}"] = int(holdings_ws[f"G{row_idx}"].value)
    holdings_ws[f"H{row_idx}"] = float(holdings_ws[f"H{row_idx}"].value)
    holdings_ws[f"I{row_idx}"] = int(holdings_ws[f"I{row_idx}"].value)

calendar_ws = wb["Coupon_Calendar"]
calendar_headers = ["Bond_ID", "Payment_Date", "Is_Maturity", "Recovery_Anchor"]
for col, header in enumerate(calendar_headers, start=1):
    calendar_ws.cell(row=1, column=col, value=header)
for row_idx, row in enumerate(calendar_rows, start=2):
    calendar_ws[f"A{row_idx}"] = row["Bond_ID"]
    calendar_ws[f"B{row_idx}"] = datetime.strptime(row["Payment_Date"], "%Y-%m-%d")
    calendar_ws[f"C{row_idx}"] = int(row["Is_Maturity"])
    calendar_ws[f"D{row_idx}"] = int(row["Recovery_Anchor"])

curves_ws = wb["Curves"]
curve_headers = ["Tenor_Years", "Base_Yield"]
write_headers_and_rows(curves_ws, curve_headers, curve_rows)
for row_idx in range(2, len(curve_rows) + 2):
    curves_ws[f"A{row_idx}"] = int(curves_ws[f"A{row_idx}"].value)
    curves_ws[f"B{row_idx}"] = float(curves_ws[f"B{row_idx}"].value)

recovery_ws = wb["Recovery_Assumptions"]
recovery_headers = ["Rating_Bucket", "Recovery_Rate"]
write_headers_and_rows(recovery_ws, recovery_headers, recovery_rows)
for row_idx in range(2, len(recovery_rows) + 2):
    recovery_ws[f"B{row_idx}"] = float(recovery_ws[f"B{row_idx}"].value)

cash_ws = wb["Cashflow_Model"]
cash_headers = [
    "Bond_ID",
    "Payment_Date",
    "Is_Maturity",
    "Recovery_Anchor",
    "Position_Face",
    "Coupon_Rate",
    "Coupon_Frequency",
    "Rating_Bucket",
    "Curve_Tenor_Years",
    "Spread_Bps",
    "Base_Curve",
    "Base_Yield",
    "Year_Fraction",
    "Coupon_CF",
    "Principal_CF",
    "Total_Contractual_CF",
    "Base_PV",
    "Base_PV_x_Time",
    "Base_PV_x_TimeSq",
    "PV_Parallel_Up_75",
    "PV_Parallel_Down_50",
    "PV_Credit_Stress",
    "Recovery_Rate",
    "Stress_Default_Flag",
]
for col, header in enumerate(cash_headers, start=1):
    cash_ws.cell(row=1, column=col, value=header)

holdings_last = len(holdings) + 1
curve_last = len(curve_rows) + 1
recovery_last = len(recovery_rows) + 1
cash_last = len(calendar_rows) + 1

for row_idx, _ in enumerate(calendar_rows, start=2):
    cal_row = row_idx
    cash_ws[f"A{row_idx}"] = f"=Coupon_Calendar!A{cal_row}"
    cash_ws[f"B{row_idx}"] = f"=Coupon_Calendar!B{cal_row}"
    cash_ws[f"C{row_idx}"] = f"=Coupon_Calendar!C{cal_row}"
    cash_ws[f"D{row_idx}"] = f"=Coupon_Calendar!D{cal_row}"
    cash_ws[f"E{row_idx}"] = f"=INDEX(Holdings!$E$2:$E${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"F{row_idx}"] = f"=INDEX(Holdings!$D$2:$D${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"G{row_idx}"] = f"=INDEX(Holdings!$F$2:$F${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"H{row_idx}"] = f"=INDEX(Holdings!$C$2:$C${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"I{row_idx}"] = f"=INDEX(Holdings!$G$2:$G${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"J{row_idx}"] = f"=INDEX(Holdings!$H$2:$H${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"K{row_idx}"] = f"=INDEX(Curves!$B$2:$B${curve_last},MATCH(I{row_idx},Curves!$A$2:$A${curve_last},0))"
    cash_ws[f"L{row_idx}"] = f"=K{row_idx}+J{row_idx}/10000"
    cash_ws[f"M{row_idx}"] = f"=MAX((B{row_idx}-Control!$B$2)/365,0)"
    cash_ws[f"N{row_idx}"] = f"=IF(M{row_idx}>0,E{row_idx}*F{row_idx}/G{row_idx},0)"
    cash_ws[f"O{row_idx}"] = f"=IF(AND(M{row_idx}>0,C{row_idx}=1),E{row_idx},0)"
    cash_ws[f"P{row_idx}"] = f"=N{row_idx}+O{row_idx}"
    cash_ws[f"Q{row_idx}"] = f"=P{row_idx}/(1+L{row_idx})^M{row_idx}"
    cash_ws[f"R{row_idx}"] = f"=Q{row_idx}*M{row_idx}"
    cash_ws[f"S{row_idx}"] = f"=Q{row_idx}*M{row_idx}^2"
    cash_ws[f"T{row_idx}"] = f"=P{row_idx}/(1+L{row_idx}+Control!$B$9/10000+Control!$C$9/10000)^M{row_idx}"
    cash_ws[f"U{row_idx}"] = f"=P{row_idx}/(1+L{row_idx}+Control!$B$10/10000+Control!$C$10/10000)^M{row_idx}"
    cash_ws[f"W{row_idx}"] = f"=INDEX(Recovery_Assumptions!$B$2:$B${recovery_last},MATCH(H{row_idx},Recovery_Assumptions!$A$2:$A${recovery_last},0))"
    cash_ws[f"X{row_idx}"] = f"=INDEX(Holdings!$I$2:$I${holdings_last},MATCH(A{row_idx},Holdings!$A$2:$A${holdings_last},0))"
    cash_ws[f"V{row_idx}"] = (
        f"=IF(X{row_idx}=1,"
        f"IF(AND(D{row_idx}=1,M{row_idx}>0),E{row_idx}*W{row_idx}*Control!$D$11/"
        f"(1+L{row_idx}+Control!$B$11/10000+Control!$C$11/10000)^M{row_idx},0),"
        f"P{row_idx}/(1+L{row_idx}+Control!$B$11/10000+Control!$C$11/10000)^M{row_idx})"
    )

scenario_ws = wb["Scenario_Valuation"]
scenario_headers = [
    "Bond_ID",
    "Issuer",
    "Rating_Bucket",
    "Base_Yield",
    "Base_Price",
    "Macaulay_Duration",
    "Modified_Duration",
    "Convexity",
    "Price_Parallel_Up_75",
    "PnL_Parallel_Up_75",
    "Price_Parallel_Down_50",
    "PnL_Parallel_Down_50",
    "Price_Credit_Stress",
    "PnL_Credit_Stress",
]
for col, header in enumerate(scenario_headers, start=1):
    scenario_ws.cell(row=1, column=col, value=header)

for row_idx in range(2, len(holdings) + 2):
    scenario_ws[f"A{row_idx}"] = f"=Holdings!A{row_idx}"
    scenario_ws[f"B{row_idx}"] = f"=Holdings!B{row_idx}"
    scenario_ws[f"C{row_idx}"] = f"=Holdings!C{row_idx}"
    scenario_ws[f"D{row_idx}"] = f"=INDEX(Cashflow_Model!$L$2:$L${cash_last},MATCH(A{row_idx},Cashflow_Model!$A$2:$A${cash_last},0))"
    scenario_ws[f"E{row_idx}"] = f"=SUMIFS(Cashflow_Model!$Q$2:$Q${cash_last},Cashflow_Model!$A$2:$A${cash_last},A{row_idx})"
    scenario_ws[f"F{row_idx}"] = f"=SUMIFS(Cashflow_Model!$R$2:$R${cash_last},Cashflow_Model!$A$2:$A${cash_last},A{row_idx})/E{row_idx}"
    scenario_ws[f"G{row_idx}"] = f"=F{row_idx}/(1+D{row_idx})"
    scenario_ws[f"H{row_idx}"] = f"=SUMIFS(Cashflow_Model!$S$2:$S${cash_last},Cashflow_Model!$A$2:$A${cash_last},A{row_idx})/E{row_idx}"
    scenario_ws[f"I{row_idx}"] = f"=SUMIFS(Cashflow_Model!$T$2:$T${cash_last},Cashflow_Model!$A$2:$A${cash_last},A{row_idx})"
    scenario_ws[f"J{row_idx}"] = f"=I{row_idx}-E{row_idx}"
    scenario_ws[f"K{row_idx}"] = f"=SUMIFS(Cashflow_Model!$U$2:$U${cash_last},Cashflow_Model!$A$2:$A${cash_last},A{row_idx})"
    scenario_ws[f"L{row_idx}"] = f"=K{row_idx}-E{row_idx}"
    scenario_ws[f"M{row_idx}"] = f"=SUMIFS(Cashflow_Model!$V$2:$V${cash_last},Cashflow_Model!$A$2:$A${cash_last},A{row_idx})"
    scenario_ws[f"N{row_idx}"] = f"=M{row_idx}-E{row_idx}"

summary_ws = wb["Portfolio_Summary"]
summary_ws["B2"] = "=SUM(Scenario_Valuation!E2:E5)"
summary_ws["B3"] = "=SUMPRODUCT(Scenario_Valuation!E2:E5,Scenario_Valuation!G2:G5)/B2"
summary_ws["B4"] = "=SUMPRODUCT(Scenario_Valuation!E2:E5,Scenario_Valuation!H2:H5)/B2"
summary_ws["B7"] = "=SUM(Scenario_Valuation!I2:I5)"
summary_ws["C7"] = "=B7-B2"
summary_ws["B8"] = "=SUM(Scenario_Valuation!K2:K5)"
summary_ws["C8"] = "=B8-B2"
summary_ws["B9"] = "=SUM(Scenario_Valuation!M2:M5)"
summary_ws["C9"] = "=B9-B2"

wb.save(OUTPUT)
PY

mkdir -p /tmp/bond-stress-recalc /root/recalc-output
cp /root/bond-stress-book.xlsx /tmp/bond-stress-recalc/bond-stress-book.xlsx
libreoffice --headless --convert-to ods --outdir /tmp/bond-stress-recalc /tmp/bond-stress-recalc/bond-stress-book.xlsx >/tmp/bond-stress-recalc/convert1.log 2>&1
if [ -f /tmp/bond-stress-recalc/bond-stress-book.ods ]; then
  libreoffice --headless --convert-to xlsx:"Calc MS Excel 2007 XML" --outdir /root/recalc-output /tmp/bond-stress-recalc/bond-stress-book.ods >/tmp/bond-stress-recalc/convert2.log 2>&1
  if [ -f /root/recalc-output/bond-stress-book.xlsx ]; then
    cp /root/recalc-output/bond-stress-book.xlsx /root/bond-stress-book.xlsx
  fi
fi
