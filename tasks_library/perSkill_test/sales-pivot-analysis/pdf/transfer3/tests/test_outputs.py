#!/usr/bin/env python3
import csv
import json
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer3_lane_priority.tsv")
SOURCE_PATH = Path("/tests/fixtures/source.json")
HEADERS = ["lane_id", "hub", "priority_tier", "risk_score", "action"]


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


def build_expected():
    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    expected = []
    for row in rows:
        risk_score, tier, action = classify(row)
        expected.append(
            {
                "lane_id": row["lane_id"],
                "hub": row["hub"],
                "priority_tier": tier,
                "risk_score": str(risk_score),
                "action": action,
            }
        )
    expected.sort(key=lambda item: (-int(item["risk_score"]), item["lane_id"]))
    return expected


def main():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        assert reader.fieldnames == HEADERS, f"unexpected headers: {reader.fieldnames}"
        actual = list(reader)
    expected = build_expected()
    assert actual == expected, "lane priority TSV does not match expected output"


if __name__ == "__main__":
    main()
