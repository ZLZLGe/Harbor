def parse_rules_doc(raw: str) -> dict[str, str]:
    """Parse a tiny colon-delimited rules document that mimics a YAML edge."""
    parsed = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def extract_rule_names(doc: dict[str, str]) -> list[str]:
    return sorted(doc)
