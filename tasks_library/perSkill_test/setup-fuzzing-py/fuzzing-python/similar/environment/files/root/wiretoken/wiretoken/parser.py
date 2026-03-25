def parse_header(text: str) -> dict[str, str]:
    pairs = {}
    for part in text.split(";"):
        if "=" not in part:
            raise ValueError("bad header")
        key, value = part.split("=", 1)
        pairs[key.strip()] = value.strip()
    return pairs


def parse_frame(data: bytes) -> dict[str, object]:
    text = data.decode("utf-8", errors="ignore").strip()
    if "|" not in text:
        raise ValueError("missing separator")
    header, payload = text.split("|", 1)
    return {
        "header": parse_header(header),
        "payload": [item.strip() for item in payload.split(",") if item.strip()],
    }
