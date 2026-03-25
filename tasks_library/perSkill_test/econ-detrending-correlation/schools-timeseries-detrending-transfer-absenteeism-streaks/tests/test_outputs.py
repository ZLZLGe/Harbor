import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_HEADER = ["district", "streak_start", "streak_end", "consecutive_months"]


def hp_cycle(values, lamb=14400.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def locate_output():
    candidates = [
        Path("/root/absenteeism_pressure_streaks.md"),
        Path.cwd() / "absenteeism_pressure_streaks.md",
        Path(__file__).resolve().parent.parent / "absenteeism_pressure_streaks.md",
    ]
    for path in candidates:
        try:
            exists = path.exists()
        except PermissionError:
            exists = False
        if exists:
            return path
    return None


def locate_input():
    candidates = [
        Path("/root/district_attendance.sqlite"),
        Path(__file__).resolve().parent.parent / "environment" / "district_attendance.sqlite",
        Path.cwd() / "environment" / "district_attendance.sqlite",
    ]
    for path in candidates:
        try:
            exists = path.exists()
        except PermissionError:
            exists = False
        if exists:
            return path
    raise FileNotFoundError("district_attendance.sqlite not found")


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


def expected_rows():
    with sqlite3.connect(locate_input()) as conn:
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
    return winners


def parse_markdown_table():
    output = locate_output()
    if output is None:
        raise FileNotFoundError("absenteeism_pressure_streaks.md not found")

    lines = [line.strip() for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 3, "Markdown table must include header, separator, and at least one data row"

    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    assert header == EXPECTED_HEADER, "Unexpected Markdown header"
    assert re.fullmatch(r"\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*){3}\|", lines[1]), "Missing Markdown separator row"

    rows = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 4, "Each data row must have 4 cells"
        assert re.fullmatch(r"\d{4}-\d{2}", cells[1]), "streak_start must use YYYY-MM"
        assert re.fullmatch(r"\d{4}-\d{2}", cells[2]), "streak_end must use YYYY-MM"
        assert re.fullmatch(r"\d+", cells[3]), "consecutive_months must be an integer"
        rows.append(
            {
                "district": cells[0],
                "streak_start": cells[1],
                "streak_end": cells[2],
                "consecutive_months": int(cells[3]),
            }
        )

    return rows


def test_output_exists():
    assert locate_output() is not None, "Missing absenteeism_pressure_streaks.md"


def test_markdown_schema_and_sorting():
    rows = parse_markdown_table()
    districts = [row["district"] for row in rows]
    assert districts == sorted(districts)


def test_rows_match_expected_winners():
    assert parse_markdown_table() == expected_rows()
