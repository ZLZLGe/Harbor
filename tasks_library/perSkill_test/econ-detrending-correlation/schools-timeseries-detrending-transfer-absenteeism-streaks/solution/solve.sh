#!/bin/bash
set -e

python3 <<'PY'
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


def hp_cycle(values, lamb=14400.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def longest_positive_streak(months, cycle):
    flags = cycle > 0
    best = None
    start = None

    for idx, flag in enumerate(flags):
        if flag and start is None:
            start = idx
        if (not flag) and start is not None:
            candidate = (idx - start, start, idx - 1)
            if best is None or candidate[0] > best[0] or (candidate[0] == best[0] and candidate[1] < best[1]):
                best = candidate
            start = None

    if start is not None:
        candidate = (len(flags) - start, start, len(flags) - 1)
        if best is None or candidate[0] > best[0] or (candidate[0] == best[0] and candidate[1] < best[1]):
            best = candidate

    return {
        "streak_start": months[best[1]],
        "streak_end": months[best[2]],
        "consecutive_months": int(best[0]),
    }


def first_accessible(candidates):
    for path in candidates:
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    return candidates[-1]


db_path = first_accessible(
    [
        Path.cwd() / "environment" / "district_attendance.sqlite",
        Path("/root/district_attendance.sqlite"),
    ]
)

with sqlite3.connect(db_path) as conn:
    data = pd.read_sql_query(
        """
        SELECT district_name, month, absenteeism_rate_pct
        FROM monthly_absenteeism
        WHERE month >= '2019-01' AND month <= '2024-12'
        ORDER BY district_name, month
        """,
        conn,
    )

results = []
for district, frame in data.groupby("district_name", sort=True):
    months = frame["month"].tolist()
    cycle = hp_cycle(frame["absenteeism_rate_pct"].to_numpy())
    streak = longest_positive_streak(months, cycle)
    results.append({"district": district, **streak})

max_months = max(row["consecutive_months"] for row in results)
winners = [row for row in results if row["consecutive_months"] == max_months]
winners.sort(key=lambda row: row["district"])

lines = [
    "| district | streak_start | streak_end | consecutive_months |",
    "| --- | --- | --- | --- |",
]
for row in winners:
    lines.append(
        f"| {row['district']} | {row['streak_start']} | {row['streak_end']} | {row['consecutive_months']} |"
    )

output_root = Path("/root/absenteeism_pressure_streaks.md")
output_repo = Path.cwd() / "absenteeism_pressure_streaks.md"
content = "\n".join(lines) + "\n"
try:
    output_root.write_text(content, encoding="utf-8")
except PermissionError:
    output_repo.write_text(content, encoding="utf-8")
PY
