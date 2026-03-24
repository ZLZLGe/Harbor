#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path
import re

import pandas as pd
import pdfplumber
from pandas.testing import assert_frame_equal

OUTPUT_FILE = Path("/root/maintenance_downtime_schedule.csv")
INPUT_FILE = "/root/maintenance_notice_packet"

EXPECTED_COLUMNS = [
    "production_line",
    "start_time",
    "end_time",
    "planned_downtime_hours",
]

ROW_PATTERN = re.compile(
    r"^(LINE-\d{2})\s+"
    r"(\d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2})\s+"
    r"(\d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2})\s+"
    r"(\d+(?:\.\d)?)\s+"
)


def parse_expected_from_notice():
    records = []
    with pdfplumber.open(INPUT_FILE) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                match = ROW_PATTERN.match(line.strip())
                if not match:
                    continue

                production_line, start_raw, end_raw, hours_raw = match.groups()
                start_dt = datetime.strptime(start_raw, "%d %b %Y %H:%M")
                end_dt = datetime.strptime(end_raw, "%d %b %Y %H:%M")
                records.append(
                    {
                        "production_line": production_line,
                        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
                        "planned_downtime_hours": float(hours_raw),
                    }
                )

    return (
        pd.DataFrame(records)
        .sort_values(["start_time", "production_line"], kind="stable")
        .reset_index(drop=True)
    )


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_columns_and_order():
    actual = pd.read_csv(OUTPUT_FILE)
    assert list(actual.columns) == EXPECTED_COLUMNS


def test_output_matches_notice_rows():
    actual = pd.read_csv(OUTPUT_FILE)
    expected = parse_expected_from_notice()
    assert_frame_equal(actual, expected, check_dtype=False)


def test_output_is_sorted():
    actual = pd.read_csv(OUTPUT_FILE)
    sorted_actual = actual.sort_values(["start_time", "production_line"], kind="stable").reset_index(drop=True)
    assert_frame_equal(actual.reset_index(drop=True), sorted_actual, check_dtype=False)


def test_timestamps_are_standardized():
    actual = pd.read_csv(OUTPUT_FILE)
    for column in ["start_time", "end_time"]:
        parsed = pd.to_datetime(actual[column], format="%Y-%m-%d %H:%M", errors="coerce")
        assert parsed.notna().all(), f"Column {column} contains non-standard timestamps"


def test_planned_hours_match_time_difference():
    actual = pd.read_csv(OUTPUT_FILE)
    start = pd.to_datetime(actual["start_time"], format="%Y-%m-%d %H:%M")
    end = pd.to_datetime(actual["end_time"], format="%Y-%m-%d %H:%M")
    duration_hours = (end - start).dt.total_seconds() / 3600
    assert ((duration_hours - actual["planned_downtime_hours"]).abs() < 1e-9).all()


def test_expected_row_count():
    actual = pd.read_csv(OUTPUT_FILE)
    assert len(actual) == 8
