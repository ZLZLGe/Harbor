#!/bin/bash
set -euo pipefail

mkdir -p /root/output

python3 <<'PY'
from shutil import copyfile

from openpyxl import load_workbook

input_path = "/root/data/scholarship-audit-template.xlsx"
output_path = "/root/output/scholarship_audit_result.xlsx"

copyfile(input_path, output_path)
wb = load_workbook(output_path)
ws = wb["Award Review"]

for row in range(11, 19):
    bursar_match = "MATCH($A{r},'Bursar Balances'!$A$2:$A$9,0)".format(r=row)
    roster_match = "MATCH($A{r},'Student Roster'!$A$2:$A$9,0)".format(r=row)

    ws[f"B{row}"] = (
        "=INDEX('Student Roster'!$C$2:$C$9,"
        + roster_match
        + ')&" "&INDEX(\'Student Roster\'!$B$2:$B$9,'
        + roster_match
        + ")"
    )
    ws[f"C{row}"] = "=INDEX('Student Roster'!$G$2:$G$9," + roster_match + ")"
    ws[f"D{row}"] = "=SUMIFS('Term Grades'!$D:$D,'Term Grades'!$A:$A,$A" + str(row) + ")"
    ws[f"E{row}"] = (
        "=SUMIFS('Term Grades'!$E:$E,'Term Grades'!$A:$A,$A"
        + str(row)
        + ")/SUMIFS('Term Grades'!$C:$C,'Term Grades'!$A:$A,$A"
        + str(row)
        + ")"
    )
    ws[f"F{row}"] = (
        "=IF(AND($E{r}>=INDEX('Award Rules'!$B$2:$B$4,1),$D{r}>=INDEX('Award Rules'!$C$2:$C$4,1)),"
        "INDEX('Award Rules'!$A$2:$A$4,1),"
        "IF(AND($E{r}>=INDEX('Award Rules'!$B$2:$B$4,2),$D{r}>=INDEX('Award Rules'!$C$2:$C$4,2)),"
        "INDEX('Award Rules'!$A$2:$A$4,2),"
        "IF(AND($E{r}>=INDEX('Award Rules'!$B$2:$B$4,3),$D{r}>=INDEX('Award Rules'!$C$2:$C$4,3)),"
        "INDEX('Award Rules'!$A$2:$A$4,3),\"Ineligible\")))"
    ).format(r=row)
    ws[f"G{row}"] = (
        "=IF(AND(OR(INDEX('Bursar Balances'!$B$2:$B$9,{m})<=500,"
        "INDEX('Bursar Balances'!$C$2:$C$9,{m})=\"Yes\"),"
        "INDEX('Bursar Balances'!$D$2:$D$9,{m})=\"None\","
        "INDEX('Bursar Balances'!$E$2:$E$9,{m})=\"Yes\"),\"Cleared\",\"Hold\")"
    ).format(m=bursar_match)
    ws[f"H{row}"] = (
        '=IF($F{r}="Ineligible","Academic Ineligible",IF($F{r}=$C{r},"Match","Mismatch"))'
    ).format(r=row)
    ws[f"I{row}"] = (
        '=IF(AND($H{r}="Match",$G{r}="Cleared"),"Approve",'
        'IF(AND($H{r}="Mismatch",$G{r}="Cleared"),"Manual Review","Hold"))'
    ).format(r=row)
    ws[f"J{row}"] = (
        '=IF($I{r}="Approve",INDEX(\'Award Rules\'!$D$2:$D$4,'
        "MATCH($C{r},'Award Rules'!$A$2:$A$4,0)),0)"
    ).format(r=row)

ws["C3"] = "=COUNTA('Student Roster'!$A$2:$A$9)"
ws["C4"] = '=COUNTIF($F$11:$F$18,"<>Ineligible")'
ws["C5"] = '=COUNTIF($H$11:$H$18,"Mismatch")'
ws["C6"] = '=COUNTIF($G$11:$G$18,"Hold")'
ws["C7"] = "=SUM($J$11:$J$18)"

wb.save(output_path)
PY
