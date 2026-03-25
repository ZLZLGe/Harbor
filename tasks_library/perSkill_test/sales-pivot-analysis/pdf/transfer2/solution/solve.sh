#!/bin/bash
set -euo pipefail

cat <<'PY' > /tmp/solve_transfer2.py
import json
from collections import defaultdict

import pdfplumber


PDF_PATH = "/root/clinic_capacity_packet.pdf"
OUTPUT_PATH = "/root/transfer2_capacity_flags.json"


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
                    if str(raw_row[0]).strip().lower() == "clinic code":
                        continue
                    clinic_code = str(raw_row[0]).strip()
                    if not clinic_code:
                        continue
                    slots = parse_int(raw_row[2])
                    booked = parse_int(raw_row[3])
                    rows.append(
                        {
                            "clinic_code": clinic_code,
                            "district": str(raw_row[1]).strip(),
                            "slots": slots,
                            "booked": booked,
                            "no_show_count": parse_int(raw_row[4]),
                            "wait_days": parse_int(raw_row[5]),
                            "utilization_pct": round(booked / slots * 100, 2),
                        }
                    )
    if not rows:
        raise RuntimeError("No clinic rows were extracted from the PDF")
    rows.sort(key=lambda item: item["clinic_code"])
    return rows


def build_output(rows):
    district_totals = defaultdict(lambda: {"slots": 0, "booked": 0, "wait_days": 0, "count": 0})
    for row in rows:
        district = row["district"]
        district_totals[district]["slots"] += row["slots"]
        district_totals[district]["booked"] += row["booked"]
        district_totals[district]["wait_days"] += row["wait_days"]
        district_totals[district]["count"] += 1

    district_utilization = []
    overflow_watchlist = []
    for district in sorted(district_totals):
        summary = district_totals[district]
        utilization_pct = round(summary["booked"] / summary["slots"] * 100, 2)
        avg_wait_days = round(summary["wait_days"] / summary["count"], 2)
        district_utilization.append(
            {
                "district": district,
                "total_slots": summary["slots"],
                "total_booked": summary["booked"],
                "utilization_pct": utilization_pct,
                "avg_wait_days": avg_wait_days,
            }
        )
        if utilization_pct >= 90.0 or avg_wait_days >= 10.0:
            overflow_watchlist.append(district)

    at_risk_clinics = [
        {
            "clinic_code": row["clinic_code"],
            "district": row["district"],
            "utilization_pct": row["utilization_pct"],
            "wait_days": row["wait_days"],
        }
        for row in rows
        if row["utilization_pct"] >= 95.0 or row["wait_days"] >= 12
    ]

    return {
        "district_utilization": district_utilization,
        "at_risk_clinics": at_risk_clinics,
        "overflow_watchlist": overflow_watchlist,
    }


def main():
    rows = load_rows()
    result = build_output(rows)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_transfer2.py
