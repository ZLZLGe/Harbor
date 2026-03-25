#!/bin/bash
set -euo pipefail

cat <<'PY' > /tmp/solve_transfer3.py
import csv

import pdfplumber


PDF_PATH = "/root/logistics_margin_packet.pdf"
OUTPUT_PATH = "/root/transfer3_lane_priority.tsv"


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
                    if str(raw_row[0]).strip().lower() == "lane id":
                        continue
                    lane_id = str(raw_row[0]).strip()
                    if not lane_id:
                        continue
                    rows.append(
                        {
                            "lane_id": lane_id,
                            "hub": str(raw_row[1]).strip(),
                            "on_time_pct": parse_int(raw_row[2]),
                            "late_stops": parse_int(raw_row[3]),
                            "fuel_variance_pct": parse_int(raw_row[4]),
                            "gross_margin": parse_int(raw_row[5]),
                        }
                    )
    if not rows:
        raise RuntimeError("No logistics rows were extracted from the PDF")
    return rows


def classify(row):
    risk_score = (100 - row["on_time_pct"]) + row["late_stops"] + max(row["fuel_variance_pct"], 0) * 2
    if risk_score >= 25 or row["gross_margin"] < 15000:
        tier = "RED"
        action = "expedite audit"
    elif risk_score >= 15:
        tier = "AMBER"
        action = "monitor next cycle"
    else:
        tier = "GREEN"
        action = "maintain plan"
    return risk_score, tier, action


def main():
    rows = []
    for row in load_rows():
        risk_score, tier, action = classify(row)
        rows.append(
            {
                "lane_id": row["lane_id"],
                "hub": row["hub"],
                "priority_tier": tier,
                "risk_score": str(risk_score),
                "action": action,
            }
        )
    rows.sort(key=lambda item: (-int(item["risk_score"]), item["lane_id"]))

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["lane_id", "hub", "priority_tier", "risk_score", "action"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_transfer3.py
