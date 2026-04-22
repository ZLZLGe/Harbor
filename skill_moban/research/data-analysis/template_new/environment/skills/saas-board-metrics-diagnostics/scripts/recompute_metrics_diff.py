#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import requests


API_URL = os.environ.get("AUDIT_API_URL", "http://127.0.0.1:8321")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: recompute_metrics_diff.py /app/output/metrics_snapshot.csv")

    path = Path(sys.argv[1])
    rows = read_csv_rows(path)
    response = requests.post(f"{API_URL}/validate-metrics", json={"metrics": rows}, timeout=30)
    payload = response.json()
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
