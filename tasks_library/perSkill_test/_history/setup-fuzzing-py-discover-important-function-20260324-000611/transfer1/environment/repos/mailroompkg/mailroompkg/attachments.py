import json


def parse_attachment_manifest(raw: str) -> list[dict[str, object]]:
    """Parse a JSON attachment manifest received from the mail gateway."""
    payload = json.loads(raw)
    return payload["attachments"]


def extract_message_parts(raw: bytes) -> list[bytes]:
    """Split a byte payload into message sections separated by a sentinel marker."""
    return [part for part in raw.split(b"\n--PART--\n") if part]


def count_binary_parts(parts: list[bytes]) -> int:
    return sum(1 for part in parts if b"\x00" in part)
