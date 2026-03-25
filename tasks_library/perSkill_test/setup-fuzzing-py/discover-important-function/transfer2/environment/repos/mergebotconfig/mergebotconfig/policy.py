def parse_rule_block(text: str) -> list[tuple[str, str]]:
    rules = []
    seen = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError("invalid rule")
        key, value = line.split("=", 1)
        key = key.strip()
        if key in seen:
            raise ValueError("duplicate env key")
        seen.add(key)
        rules.append((key, value.strip()))
    return rules


def parse_schedule(text: str) -> tuple[int, int]:
    hour, minute = text.split(":", 1)
    hour_i = int(hour)
    minute_i = int(minute)
    if minute_i < 0 or minute_i > 59:
        raise ValueError("minute out of range")
    return hour_i, minute_i


def load_policy_document(text: str) -> dict[str, object]:
    sections = [segment for segment in text.split("\n\n") if segment.strip()]
    return {"rules": [line for line in sections[0].splitlines() if line.strip()], "count": len(sections)}
