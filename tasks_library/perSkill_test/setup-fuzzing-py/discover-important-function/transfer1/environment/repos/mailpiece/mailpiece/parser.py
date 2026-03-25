from .headers import parse_headers
from .parts import parse_boundary_section


def parse_message(raw: bytes) -> dict[str, object]:
    text = raw.decode("utf-8")
    if "\n\n" not in text:
        raise ValueError("missing separator")
    header_text, body = text.split("\n\n", 1)
    headers = parse_headers(header_text)
    parts = parse_boundary_section(body, headers.get("boundary", ""))
    return {"headers": headers, "parts": parts}
