import csv
import io


def load_archive_index(raw: str) -> list[dict[str, str]]:
    """Load an archive index CSV that controls downstream export jobs."""
    return [dict(row) for row in csv.DictReader(io.StringIO(raw))]


def archived_objects(rows: list[dict[str, str]]) -> int:
    return len(rows)
