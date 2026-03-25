def parse_headers(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if ":" not in line:
            raise ValueError("invalid header")
        key, value = line.split(":", 1)
        result[key.strip().lower()] = value.strip()
    return result
