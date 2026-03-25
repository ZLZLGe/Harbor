def parse_scalar(value: str):
    value = value.strip()
    if value.isdigit():
        return int(value)
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def load_document(text: str) -> dict[str, object]:
    result = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError("invalid line")
        key, value = line.split(":", 1)
        result[key.strip()] = parse_scalar(value)
    return result


def merge_overrides(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    merged.update(override)
    return merged
