import re
from datetime import datetime, timezone
from pathlib import Path

import pytest


OUTPUT_PATH = Path("/root/output/maintenance_window_forecast.md")
TITLE = "# API Maintenance Window Forecast"
EXPECTED_RECURRENCE_HOURS = 18.0
EXPECTED_WINDOW_MINUTES = 50.0
EXPECTED_FIRST_START = "2025-04-01T03:30:00Z"
EXPECTED_NEXT_START = "2025-04-01T21:30:00Z"


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def parsed_output():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/maintenance_window_forecast.md"
    raw = OUTPUT_PATH.read_text(encoding="utf-8")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    assert lines[0] == TITLE, "Markdown 标题不符合要求"
    assert len(lines) == 5, "输出只能包含标题和 4 行项目符号"

    patterns = {
        "recurrence_hours": r"^- recurrence_hours: (-?\d+(?:\.(\d+))?)$",
        "window_minutes": r"^- window_minutes: (-?\d+(?:\.(\d+))?)$",
        "first_window_start_utc": r"^- first_window_start_utc: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$",
        "next_window_start_utc": r"^- next_window_start_utc: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$",
    }

    values = {}
    for key, line in zip(patterns, lines[1:]):
        match = re.fullmatch(patterns[key], line)
        assert match is not None, f"{key} 行格式不符合要求"
        values[key] = match.group(1)
        if key in {"recurrence_hours", "window_minutes"}:
            decimals = match.group(2) or ""
            assert len(decimals) <= 5, f"{key} 需要保留到小数点后 5 位以内"

    values["recurrence_hours"] = float(values["recurrence_hours"])
    values["window_minutes"] = float(values["window_minutes"])
    values["first_window_start_utc"] = parse_timestamp(values["first_window_start_utc"])
    values["next_window_start_utc"] = parse_timestamp(values["next_window_start_utc"])
    return values


def minutes_apart(actual: datetime, expected: str) -> float:
    target = parse_timestamp(expected)
    return abs((actual - target).total_seconds()) / 60.0


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/maintenance_window_forecast.md"


def test_basic_schema(parsed_output):
    assert parsed_output["recurrence_hours"] > 0
    assert parsed_output["window_minutes"] > 0
    assert parsed_output["next_window_start_utc"] > parsed_output["first_window_start_utc"]


def test_forecast_matches_periodic_window(parsed_output):
    assert abs(parsed_output["recurrence_hours"] - EXPECTED_RECURRENCE_HOURS) < 0.25
    assert abs(parsed_output["window_minutes"] - EXPECTED_WINDOW_MINUTES) < 10.0
    assert minutes_apart(parsed_output["first_window_start_utc"], EXPECTED_FIRST_START) <= 15.0
    assert minutes_apart(parsed_output["next_window_start_utc"], EXPECTED_NEXT_START) <= 15.0


def test_next_window_consistent_with_recurrence(parsed_output):
    gap_hours = (
        parsed_output["next_window_start_utc"] - parsed_output["first_window_start_utc"]
    ).total_seconds() / 3600.0
    assert abs(gap_hours - parsed_output["recurrence_hours"]) < 0.02
