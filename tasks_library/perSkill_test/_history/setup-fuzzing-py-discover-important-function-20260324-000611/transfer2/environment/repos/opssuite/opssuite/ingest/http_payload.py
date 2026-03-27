import json


def parse_ingest_request(raw: bytes) -> dict[str, object]:
    """Decode inbound HTTP payload bytes into a JSON request object."""
    return json.loads(raw.decode("utf-8"))


def normalize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value.strip() for key, value in headers.items()}
