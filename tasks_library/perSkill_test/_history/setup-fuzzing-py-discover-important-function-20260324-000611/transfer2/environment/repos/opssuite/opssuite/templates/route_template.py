def parse_route_template(raw: str) -> list[str]:
    """Split a path template into literal segments and placeholders."""
    return [part for part in raw.replace("}", "{").split("{") if part]


def placeholder_count(parts: list[str]) -> int:
    return sum(1 for part in parts if "/" not in part and "-" not in part)
