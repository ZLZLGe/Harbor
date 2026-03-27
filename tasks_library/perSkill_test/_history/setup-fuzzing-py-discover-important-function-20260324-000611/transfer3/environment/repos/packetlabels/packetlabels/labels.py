def parse_label_row(raw: str) -> dict[str, str]:
    """Parse a comma-delimited shipping label row."""
    label_id, zone, status = raw.split(",")
    return {"label_id": label_id, "zone": zone, "status": status}


def decode_label_frame(raw: bytes) -> list[dict[str, str]]:
    """Decode newline-delimited label rows from a device frame."""
    return [parse_label_row(line) for line in raw.decode("utf-8").splitlines() if line]


def active_labels(rows: list[dict[str, str]]) -> int:
    return sum(1 for row in rows if row["status"] == "active")
