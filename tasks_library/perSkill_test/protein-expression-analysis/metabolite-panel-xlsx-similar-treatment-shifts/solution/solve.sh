#!/bin/bash
set -euo pipefail

EXCEL_FILE="/root/metabolite_treatment_shift_scorecard.xlsx"

cat > /tmp/solve_metabolite_shift.py <<'PY'
from openpyxl import load_workbook

EXCEL_FILE = "/root/metabolite_treatment_shift_scorecard.xlsx"


def main():
    wb = load_workbook(EXCEL_FILE)
    task = wb["Task"]

    for row in range(11, 19):
        for col in "CDEFGHIJKL":
            task[f"{col}{row}"] = (
                f"=INDEX(Data!$D$2:$BA$201,"
                f"MATCH($A{row},Data!$A$2:$A$201,0),"
                f"MATCH({col}$10,Data!$D$1:$BA$1,0))"
            )

    summary_columns = list("BCDEFGHI")

    for offset, col in enumerate(summary_columns, start=11):
        task[f"{col}24"] = (
            f'=SUMPRODUCT(($C$9:$L$9="Responder")*C{offset}:L{offset})/'
            'COUNTIF($C$9:$L$9,"Responder")'
        )
        task[f"{col}25"] = (
            f'=SQRT(SUMPRODUCT(($C$9:$L$9="Responder")*'
            f'(C{offset}:L{offset}-{col}24)^2)/'
            '((COUNTIF($C$9:$L$9,"Responder")-1)))'
        )
        task[f"{col}26"] = (
            f'=SUMPRODUCT(($C$9:$L$9="Nonresponder")*C{offset}:L{offset})/'
            'COUNTIF($C$9:$L$9,"Nonresponder")'
        )
        task[f"{col}27"] = (
            f'=SQRT(SUMPRODUCT(($C$9:$L$9="Nonresponder")*'
            f'(C{offset}:L{offset}-{col}26)^2)/'
            '((COUNTIF($C$9:$L$9,"Nonresponder")-1)))'
        )

    for row, col in zip(range(32, 40), summary_columns):
        task[f"C{row}"] = f"={col}24-{col}26"
        task[f"D{row}"] = f"=2^C{row}"
        task[f"E{row}"] = f"=ABS(C{row})"

    for row in range(32, 36):
        task[f"I{row}"] = f"=INDEX($A$32:$A$39,MATCH(LARGE($E$32:$E$39,H{row}),$E$32:$E$39,0))"
        task[f"J{row}"] = f"=INDEX($B$32:$B$39,MATCH(LARGE($E$32:$E$39,H{row}),$E$32:$E$39,0))"
        task[f"K{row}"] = f"=LARGE($E$32:$E$39,H{row})"
        task[f"L{row}"] = (
            f'=IF(INDEX($C$32:$C$39,MATCH(K{row},$E$32:$E$39,0))>0,'
            '"Higher in Responder","Higher in Nonresponder")'
        )

    wb.save(EXCEL_FILE)
    wb.close()


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_metabolite_shift.py
python3 /root/.codex/skills/xlsx/recalc.py "$EXCEL_FILE"
