#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from decimal import Decimal, ROUND_HALF_UP
from openpyxl import Workbook

INPUT_PATH = "/app/workspace/scores.tsv"
OUTPUT_PATH = "/app/workspace/transfer3.xlsx"


def grade_of(score: Decimal) -> str:
    if score >= Decimal("90"):
        return "A"
    if score >= Decimal("80"):
        return "B"
    if score >= Decimal("70"):
        return "C"
    if score >= Decimal("60"):
        return "D"
    return "F"


rows = []
with open(INPUT_PATH, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for item in reader:
        student = (item.get("student") or "").strip()
        quiz = Decimal((item.get("quiz") or "0").strip())
        midterm = Decimal((item.get("midterm") or "0").strip())
        final = Decimal((item.get("final") or "0").strip())

        score = (
            quiz * Decimal("0.2")
            + midterm * Decimal("0.3")
            + final * Decimal("0.5")
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

        rows.append(
            {
                "student": student,
                "final_score": score,
                "grade": grade_of(score),
            }
        )

rows.sort(key=lambda row: (-row["final_score"], row["student"]))

wb = Workbook()
ws = wb.active
ws.title = "report"
ws.append(["student", "final_score", "grade"])
for row in rows:
    ws.append([row["student"], f"{row['final_score']:.1f}", row["grade"]])

wb.save(OUTPUT_PATH)
PY
