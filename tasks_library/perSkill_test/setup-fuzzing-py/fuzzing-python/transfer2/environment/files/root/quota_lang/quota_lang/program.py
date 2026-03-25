def parse_program(text: str) -> list[tuple[str, int]]:
    steps = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError("bad step")
        op, value_text = parts
        if op not in {"limit", "reserve"}:
            raise ValueError("bad op")
        steps.append((op, int(value_text)))
    return steps
