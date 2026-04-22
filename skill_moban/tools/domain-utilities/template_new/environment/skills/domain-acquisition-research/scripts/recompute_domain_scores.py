#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    output_path = Path("/app/output/opportunity_report.json")
    if not output_path.exists():
        print("No /app/output/opportunity_report.json found yet.")
        return

    report = json.loads(output_path.read_text(encoding="utf-8"))
    print("Current ranked buy_now domains:")
    for domain in report.get("buy_now_ranked", []):
        print(f"- {domain}")

    print("\nEvaluations present:")
    for row in sorted(report.get("evaluations", []), key=lambda item: item["domain"]):
        print(
            f"{row['domain']}: status={row['status']} total={row['total_score']} "
            f"ceiling={row['price_ceiling_usd']}"
        )

    candidates = list(
        csv.DictReader(Path("/app/data/candidate_domains.csv").read_text(encoding="utf-8").splitlines())
    )
    print(f"\nCandidate count: {len(candidates)}")


if __name__ == "__main__":
    main()
