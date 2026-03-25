def parse_coupon_note(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError("bad coupon line")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    if "code" not in result:
        raise ValueError("missing code")
    return result
