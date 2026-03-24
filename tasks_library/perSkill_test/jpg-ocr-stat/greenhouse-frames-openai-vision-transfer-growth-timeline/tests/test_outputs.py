from pathlib import Path


OUTPUT_FILE = Path("/app/workspace/growth_timeline.tsv")
EXPECTED_DAILY_ROWS = [
    ("2025-04-01", 2, 0, 1),
    ("2025-04-02", 3, 1, 1),
    ("2025-04-03", 4, 2, 2),
    ("2025-04-04", 5, 4, 3),
    ("2025-04-05", 5, 6, 2),
    ("2025-04-06", 4, 7, 4),
    ("2025-04-07", 3, 5, 4),
]
EXPECTED_PEAK_ROWS = [
    ("flowering_plants", "2025-04-04", 5),
    ("ripe_fruits", "2025-04-06", 7),
    ("diseased_leaves", "2025-04-06", 4),
]


def split_sections(lines):
    assert lines, "Output file is empty"
    assert lines[0] == "[daily_counts]", "First section must be [daily_counts]"

    try:
        peak_index = lines.index("[peak_dates]")
    except ValueError as exc:
        raise AssertionError("Missing [peak_dates] section") from exc

    daily_lines = lines[:peak_index]
    peak_lines = lines[peak_index:]
    return daily_lines, peak_lines


def parse_daily(lines):
    assert lines[0] == "[daily_counts]"
    assert len(lines) == 2 + len(EXPECTED_DAILY_ROWS) + 1, "Unexpected number of lines in daily section"
    assert lines[1] == "date\tflowering_plants\tripe_fruits\tdiseased_leaves", "Daily header mismatch"
    assert lines[-1] == "", "Daily section must end with exactly one blank line before [peak_dates]"

    rows = []
    for line in lines[2:-1]:
        parts = line.split("\t")
        assert len(parts) == 4, f"Unexpected daily row: {line}"
        date, flowering, fruits, diseased = parts
        rows.append((date, int(flowering), int(fruits), int(diseased)))
    return rows


def parse_peaks(lines):
    assert lines[0] == "[peak_dates]"
    assert len(lines) == 2 + len(EXPECTED_PEAK_ROWS), "Unexpected number of lines in peak section"
    assert lines[1] == "metric\tpeak_date\tpeak_value", "Peak header mismatch"

    rows = []
    for line in lines[2:]:
        parts = line.split("\t")
        assert len(parts) == 3, f"Unexpected peak row: {line}"
        metric, peak_date, peak_value = parts
        rows.append((metric, peak_date, int(peak_value)))
    return rows


def earliest_peak_from_daily(daily_rows, column_index):
    best = daily_rows[0]
    for row in daily_rows[1:]:
        if row[column_index] > best[column_index]:
            best = row
    return best[0], best[column_index]


def test_growth_timeline_tsv():
    assert OUTPUT_FILE.exists(), "Missing /app/workspace/growth_timeline.tsv"

    text = OUTPUT_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()
    daily_lines, peak_lines = split_sections(lines)

    daily_rows = parse_daily(daily_lines)
    peak_rows = parse_peaks(peak_lines)

    assert daily_rows == EXPECTED_DAILY_ROWS, f"Daily rows mismatch: {daily_rows}"
    assert peak_rows == EXPECTED_PEAK_ROWS, f"Peak rows mismatch: {peak_rows}"

    dates = [row[0] for row in daily_rows]
    assert dates == sorted(dates), "Daily rows must be sorted by date"

    peak_map = {metric: (peak_date, peak_value) for metric, peak_date, peak_value in peak_rows}
    assert peak_map["flowering_plants"] == earliest_peak_from_daily(daily_rows, 1)
    assert peak_map["ripe_fruits"] == earliest_peak_from_daily(daily_rows, 2)
    assert peak_map["diseased_leaves"] == earliest_peak_from_daily(daily_rows, 3)

    assert text.count("[daily_counts]") == 1, "Output must contain exactly one [daily_counts] section"
    assert text.count("[peak_dates]") == 1, "Output must contain exactly one [peak_dates] section"
