#!/bin/bash
set -euo pipefail

EXCEL_FILE="/root/campus_energy_tariff_variance.xlsx"

cat > /tmp/solve_campus_energy.py <<'PY'
from openpyxl import load_workbook

EXCEL_FILE = "/root/campus_energy_tariff_variance.xlsx"


def main():
    wb = load_workbook(EXCEL_FILE)
    review = wb["Tariff Review"]

    for row in range(8, 18):
        review[f"F{row}"] = (
            f'=SUMIFS(MeterData!$F$2:$F$11,'
            f'MeterData!$A$2:$A$11,$A{row},'
            f'MeterData!$B$2:$B$11,$B{row},'
            f'MeterData!$C$2:$C$11,$C{row},'
            f'MeterData!$D$2:$D$11,$D{row},'
            f'MeterData!$E$2:$E$11,$E{row})'
        )
        review[f"G{row}"] = (
            f'=SUMIFS(Rates!$C$2:$C$11,'
            f'Rates!$A$2:$A$11,$D{row},'
            f'Rates!$B$2:$B$11,$E{row})'
        )
        review[f"H{row}"] = f"=F{row}*G{row}"

    for row in range(23, 28):
        review[f"B{row}"] = f'=SUMIFS($H$8:$H$17,$B$8:$B$17,$A{row},$E$8:$E$17,"Peak")'
        review[f"C{row}"] = f'=SUMIFS($H$8:$H$17,$B$8:$B$17,$A{row},$E$8:$E$17,"Valley")'
        review[f"D{row}"] = f"=B{row}+C{row}"
        review[f"E{row}"] = f'=SUMIF(Budget!$A$2:$A$6,$A{row},Budget!$B$2:$B$6)'
        review[f"F{row}"] = f"=D{row}-E{row}"
        review[f"G{row}"] = f'=SUMIF(Budget!$A$2:$A$6,$A{row},Budget!$C$2:$C$6)'
        review[f"H{row}"] = (
            f'=SUMIFS($F$8:$F$17,$B$8:$B$17,$A{row},$E$8:$E$17,"Peak")'
            f'*G{row}*('
            f'SUMIFS($G$8:$G$17,$B$8:$B$17,$A{row},$E$8:$E$17,"Peak")-'
            f'SUMIFS($G$8:$G$17,$B$8:$B$17,$A{row},$E$8:$E$17,"Valley"))'
        )
        review[f"I{row}"] = (
            f'=IF(AND(F{row}>0,H{row}>=300),"Act Now",'
            f'IF(H{row}>=200,"Plan Shift","Track"))'
        )

    for row in range(32, 36):
        review[f"J{row}"] = f'=INDEX($A$23:$A$27,MATCH(LARGE($H$23:$H$27,$I{row}),$H$23:$H$27,0))'
        review[f"K{row}"] = f'=INDEX($D$23:$D$27,MATCH(LARGE($H$23:$H$27,$I{row}),$H$23:$H$27,0))'
        review[f"L{row}"] = f'=INDEX($F$23:$F$27,MATCH(LARGE($H$23:$H$27,$I{row}),$H$23:$H$27,0))'
        review[f"M{row}"] = f'=LARGE($H$23:$H$27,$I{row})'
        review[f"N{row}"] = f'=INDEX($I$23:$I$27,MATCH($M{row},$H$23:$H$27,0))'

    wb.save(EXCEL_FILE)
    wb.close()


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_campus_energy.py
python3 /root/.codex/skills/xlsx/recalc.py "$EXCEL_FILE"
