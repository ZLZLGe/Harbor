#!/bin/bash
set -euo pipefail

cd /root

cat > /tmp/solve_league_standings.py <<'PY'
from openpyxl import load_workbook

FILE = "/root/league_standings_review.xlsx"

wb = load_workbook(FILE)
review = wb["Review"]

team_rows = range(8, 16)
results_last_row = 19
teams_last_row = 9

for row in team_rows:
    review[f"B{row}"] = f'=INDEX(Teams!$B$2:$B${teams_last_row},MATCH($A{row},Teams!$A$2:$A${teams_last_row},0))'
    review[f"C{row}"] = (
        f'=SUMPRODUCT((Results!$C$2:$C${results_last_row}="Final")'
        f'*(Results!$D$2:$D${results_last_row}=$A{row})'
        f'*(Results!$F$2:$F${results_last_row}>Results!$G$2:$G${results_last_row}))'
        f'+SUMPRODUCT((Results!$C$2:$C${results_last_row}="Final")'
        f'*(Results!$E$2:$E${results_last_row}=$A{row})'
        f'*(Results!$G$2:$G${results_last_row}>Results!$F$2:$F${results_last_row}))'
    )
    review[f"D{row}"] = (
        f'=SUMPRODUCT((Results!$C$2:$C${results_last_row}="Final")'
        f'*((Results!$D$2:$D${results_last_row}=$A{row})+(Results!$E$2:$E${results_last_row}=$A{row}))'
        f'*(Results!$F$2:$F${results_last_row}=Results!$G$2:$G${results_last_row}))'
    )
    review[f"E{row}"] = (
        f'=SUMPRODUCT((Results!$C$2:$C${results_last_row}="Final")'
        f'*(Results!$D$2:$D${results_last_row}=$A{row})'
        f'*(Results!$F$2:$F${results_last_row}<Results!$G$2:$G${results_last_row}))'
        f'+SUMPRODUCT((Results!$C$2:$C${results_last_row}="Final")'
        f'*(Results!$E$2:$E${results_last_row}=$A{row})'
        f'*(Results!$G$2:$G${results_last_row}<Results!$F$2:$F${results_last_row}))'
    )
    review[f"F{row}"] = (
        f'=SUMIFS(Results!$F$2:$F${results_last_row},Results!$C$2:$C${results_last_row},"Final",Results!$D$2:$D${results_last_row},$A{row})'
        f'+SUMIFS(Results!$G$2:$G${results_last_row},Results!$C$2:$C${results_last_row},"Final",Results!$E$2:$E${results_last_row},$A{row})'
    )
    review[f"G{row}"] = (
        f'=SUMIFS(Results!$G$2:$G${results_last_row},Results!$C$2:$C${results_last_row},"Final",Results!$D$2:$D${results_last_row},$A{row})'
        f'+SUMIFS(Results!$F$2:$F${results_last_row},Results!$C$2:$C${results_last_row},"Final",Results!$E$2:$E${results_last_row},$A{row})'
    )
    review[f"H{row}"] = f"=F{row}-G{row}"
    review[f"I{row}"] = f"=C{row}*3+D{row}"
    review[f'J{row}'] = (
        f'=1'
        f'+SUMPRODUCT(($I$8:$I$15>I{row})*1)'
        f'+SUMPRODUCT(($I$8:$I$15=I{row})*($H$8:$H$15>H{row})*1)'
        f'+SUMPRODUCT(($I$8:$I$15=I{row})*($H$8:$H$15=H{row})*($F$8:$F$15>F{row})*1)'
        f'+SUMPRODUCT(($I$8:$I$15=I{row})*($H$8:$H$15=H{row})*($F$8:$F$15=F{row})*($A$8:$A$15<A{row})*1)'
    )

review["L3"] = f'=COUNTIF(Results!$C$2:$C${results_last_row},"Final")'
review["M3"] = (
    f'=SUMIFS(Results!$F$2:$F${results_last_row},Results!$C$2:$C${results_last_row},"Final")'
    f'+SUMIFS(Results!$G$2:$G${results_last_row},Results!$C$2:$C${results_last_row},"Final")'
)
review["N3"] = '=INDEX($A$8:$A$15,MATCH(1,$J$8:$J$15,0))'

for row in range(8, 16):
    review[f"L{row}"] = f'=ROWS($L$8:L{row})'
    review[f"M{row}"] = f'=INDEX($A$8:$A$15,MATCH($L{row},$J$8:$J$15,0))'
    review[f"N{row}"] = f'=INDEX($B$8:$B$15,MATCH($L{row},$J$8:$J$15,0))'
    review[f"O{row}"] = f'=INDEX($I$8:$I$15,MATCH($L{row},$J$8:$J$15,0))'
    review[f"P{row}"] = f'=INDEX($H$8:$H$15,MATCH($L{row},$J$8:$J$15,0))'
    review[f"Q{row}"] = f'=INDEX($F$8:$F$15,MATCH($L{row},$J$8:$J$15,0))'
    review[f"R{row}"] = f'=IF($L{row}<=2,"PROMOTION",IF($L{row}<=4,"PLAYOFF",IF($L{row}>=7,"RELEGATION","SAFE")))'

wb.save(FILE)
wb.close()
PY

python3 /tmp/solve_league_standings.py
python3 /root/.codex/skills/xlsx/recalc.py /root/league_standings_review.xlsx
