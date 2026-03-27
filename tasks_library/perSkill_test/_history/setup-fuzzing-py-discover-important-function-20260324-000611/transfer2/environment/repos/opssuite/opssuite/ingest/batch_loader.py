import json


def load_batch_manifest(raw: str) -> list[dict[str, object]]:
    """Load newline-delimited JSON manifest records."""
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def batch_ids(rows: list[dict[str, object]]) -> list[str]:
    return [str(row["batch_id"]) for row in rows]
