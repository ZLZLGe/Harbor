#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path


ROOT = Path(os.environ.get("BOARD_DATA_ROOT", "/app/data"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    metrics = defaultdict(list)
    for row in read_csv_rows(ROOT / "subscriptions" / "account_month_status.csv"):
        key = (row["segment"], row["channel"])
        start_arr = float(row["start_arr_usd"])
        end_arr = float(row["end_arr_usd"])
        value = 0.0
        if start_arr == 0 and end_arr > 0:
            value = end_arr
        elif start_arr > 0 and end_arr > 0:
            value = end_arr - start_arr
        elif start_arr > 0 and end_arr == 0:
            value = -start_arr
        metrics[key].append((row["month"], value))

    print("Segment/channel net-ARR signal by month")
    for key in sorted(metrics):
        monthly = defaultdict(float)
        for month, value in metrics[key]:
            monthly[month] += value
        ordered = [f"{month}={monthly[month]:.2f}" for month in sorted(monthly)]
        print(f"{key[0]} | {key[1]} -> " + ", ".join(ordered))


if __name__ == "__main__":
    main()
