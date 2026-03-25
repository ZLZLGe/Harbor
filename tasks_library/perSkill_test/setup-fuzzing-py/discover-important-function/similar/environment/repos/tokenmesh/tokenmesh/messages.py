def split_mesh_packet(text: str) -> list[str]:
    parts = [segment.strip() for segment in text.split("|")]
    return [part for part in parts if part]


def expand_aliases(tokens: list[str], aliases: dict[str, list[str]]) -> list[str]:
    expanded = []
    for token in tokens:
        if token in aliases:
            expanded.extend(aliases[token])
        else:
            expanded.append(token)
    return expanded


def parse_mesh_packet(text: str) -> dict[str, object]:
    tokens = split_mesh_packet(text)
    if len(tokens) < 2:
        raise ValueError("not enough tokens")
    header = tokens[0]
    values = expand_aliases(tokens[1:], {"burst": ["b1", "b2"]})
    return {"header": header, "values": values}
