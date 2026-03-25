def parse_node_record(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError("missing separator")
    node_id, label = line.split(":", 1)
    return node_id.strip(), label.strip()


def parse_bundle(text: str) -> dict[str, object]:
    nodes = []
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        nodes.append(parse_node_record(raw_line))
    return {"nodes": nodes, "count": len(nodes)}
