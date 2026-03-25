#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from clickstream_fixture import write_clickstream


SOLUTION_PATH = Path("/root/workspace/session_rollup_solution.py")
BASELINE_PATH = Path("/root/workspace/session_rollup_baseline.py")
SAMPLE_INPUT_PATH = Path("/root/workspace/sample_clickstream.ndjson")
EXPECTED_FIELDS = [
    "session_id",
    "user_id",
    "event_count",
    "session_duration_seconds",
    "entry_page",
    "converted",
]
MEMORY_LIMIT_MB = 180
RSS_PATTERN = re.compile(r"Maximum resident set size \(kbytes\):\s+(\d+)")


def read_csv_rows(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def run_rollup(script_path: Path, input_path: Path, output_path: Path):
    subprocess.run(
        [sys.executable, str(script_path), "--input", str(input_path), "--output", str(output_path)],
        check=True,
    )
    return read_csv_rows(output_path)


def oracle_rows(input_path: Path):
    rows = []
    current = None

    with input_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            session_id = str(event["session_id"])
            event_time = int(event["event_time"])

            if current is None or session_id != current["session_id"]:
                if current is not None:
                    rows.append(
                        {
                            "session_id": current["session_id"],
                            "user_id": current["user_id"],
                            "event_count": str(current["event_count"]),
                            "session_duration_seconds": str(
                                current["last_event_time"] - current["first_event_time"]
                            ),
                            "entry_page": current["entry_page"],
                            "converted": "1" if current["converted"] else "0",
                        }
                    )
                current = {
                    "session_id": session_id,
                    "user_id": str(event["user_id"]),
                    "event_count": 1,
                    "first_event_time": event_time,
                    "last_event_time": event_time,
                    "entry_page": str(event["page"]),
                    "converted": event["event_type"] == "purchase",
                }
                continue

            current["event_count"] += 1
            current["last_event_time"] = event_time
            if event["event_type"] == "purchase":
                current["converted"] = True

    if current is not None:
        rows.append(
            {
                "session_id": current["session_id"],
                "user_id": current["user_id"],
                "event_count": str(current["event_count"]),
                "session_duration_seconds": str(current["last_event_time"] - current["first_event_time"]),
                "entry_page": current["entry_page"],
                "converted": "1" if current["converted"] else "0",
            }
        )

    return rows


def test_solution_file_exists():
    assert SOLUTION_PATH.exists(), "missing /root/workspace/session_rollup_solution.py"


def test_sample_input_contract(tmp_path: Path):
    output_path = tmp_path / "sample_rollup.csv"
    fieldnames, rows = run_rollup(SOLUTION_PATH, SAMPLE_INPUT_PATH, output_path)

    assert fieldnames == EXPECTED_FIELDS
    assert rows == oracle_rows(SAMPLE_INPUT_PATH)


def test_matches_baseline_on_small_generated_fixture(tmp_path: Path):
    input_path = tmp_path / "small_clickstream.ndjson"
    baseline_output = tmp_path / "baseline.csv"
    solution_output = tmp_path / "solution.csv"

    write_clickstream(input_path, num_sessions=180, seed=13)

    _, expected_rows = run_rollup(BASELINE_PATH, input_path, baseline_output)
    _, produced_rows = run_rollup(SOLUTION_PATH, input_path, solution_output)
    assert produced_rows == expected_rows


def test_large_fixture_correctness_and_contract(tmp_path: Path):
    input_path = tmp_path / "full_clickstream.ndjson"
    output_path = tmp_path / "full_rollup.csv"

    write_clickstream(input_path, num_sessions=12000, seed=33)

    fieldnames, produced_rows = run_rollup(SOLUTION_PATH, input_path, output_path)
    expected_rows = oracle_rows(input_path)

    assert fieldnames == EXPECTED_FIELDS
    assert produced_rows == expected_rows
    for row in produced_rows[:50]:
        assert set(row) == set(EXPECTED_FIELDS)
        assert row["event_count"].isdigit()
        assert row["session_duration_seconds"].isdigit()
        assert row["converted"] in {"0", "1"}


def test_memory_budget_on_large_fixture(tmp_path: Path):
    input_path = tmp_path / "memory_clickstream.ndjson"
    output_path = tmp_path / "memory_rollup.csv"

    write_clickstream(input_path, num_sessions=65000, seed=61)

    completed = subprocess.run(
        [
            "/usr/bin/time",
            "-v",
            sys.executable,
            str(SOLUTION_PATH),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    match = RSS_PATTERN.search(completed.stderr)
    assert match, completed.stderr
    rss_mb = int(match.group(1)) / 1024
    assert rss_mb <= MEMORY_LIMIT_MB, f"peak RSS {rss_mb:.1f} MB exceeds {MEMORY_LIMIT_MB} MB"

    fieldnames, _rows = read_csv_rows(output_path)
    assert fieldnames == EXPECTED_FIELDS
