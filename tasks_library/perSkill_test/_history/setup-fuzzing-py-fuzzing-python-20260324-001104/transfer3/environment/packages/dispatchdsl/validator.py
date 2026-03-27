def validate_tokens(tokens: list[str]) -> dict[str, object]:
    if not tokens:
        return {"status": "empty"}

    first = tokens[0]
    if "=" not in first:
        return {"status": "missing-equals"}

    key, value = first.split("=", 1)
    key = key.strip().lower()
    value = value.strip()

    if key == "route" and value.startswith("ops/") and len(tokens) > 1:
        return {"status": "ops-route", "steps": len(tokens)}
    if key == "mode" and value in {"drain", "burst"}:
        return {"status": "mode", "value": value}
    return {"status": "ok", "key": key}
