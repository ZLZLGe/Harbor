#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer2_capacity_flags.json")
SOURCE_PATH = Path("/tests/fixtures/source.json")


def build_expected():
    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    rows.sort(key=lambda item: item["clinic_code"])
    for row in rows:
        row["utilization_pct"] = round(row["booked"] / row["slots"] * 100, 2)

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

    return {
        "district_utilization": district_utilization,
        "at_risk_clinics": [
            {
                "clinic_code": row["clinic_code"],
                "district": row["district"],
                "utilization_pct": row["utilization_pct"],
                "wait_days": row["wait_days"],
            }
            for row in rows
            if row["utilization_pct"] >= 95.0 or row["wait_days"] >= 12
        ],
        "overflow_watchlist": overflow_watchlist,
    }


def main():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    actual = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = build_expected()
    assert list(actual.keys()) == list(expected.keys()), f"unexpected keys: {list(actual.keys())}"
    assert actual == expected, "clinic capacity output does not match expected JSON"


if __name__ == "__main__":
    main()
