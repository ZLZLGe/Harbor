import csv
import io


def parse_window_row(raw: str) -> dict[str, str]:
    """Parse a maintenance window row using pipe separators."""
    window_id, start, end = raw.split("|")
    return {"window_id": window_id, "start": start, "end": end}


def load_window_table(raw: str) -> list[dict[str, str]]:
    """Load a CSV table of maintenance windows."""
    return [dict(row) for row in csv.DictReader(io.StringIO(raw))]


def duration_hours(row: dict[str, str]) -> int:
    return int(row["hours"])
