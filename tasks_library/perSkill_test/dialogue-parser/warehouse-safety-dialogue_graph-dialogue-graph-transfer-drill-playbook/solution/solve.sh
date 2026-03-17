#!/bin/bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:/app/environment/skills/dialogue_graph/scripts:/root/.codex/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts"

python3 - <<'PY'
import os
import sys

for candidate in [
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.codex/skills/dialogue_graph/scripts",
    "/root/.claude/skills/dialogue_graph/scripts",
    "environment/skills/dialogue_graph/scripts",
]:
    if os.path.exists(candidate):
        sys.path.insert(0, candidate)

from dialogue_graph import Edge, Graph, Node


def find_input_path() -> str:
    for candidate in [
        "/app/drill_playbook.txt",
        "drill_playbook.txt",
        "environment/drill_playbook.txt",
    ]:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("drill_playbook.txt not found")


def split_transition(line: str) -> tuple[str, str]:
    if "->" not in line:
        raise ValueError(f"Missing transition arrow in line: {line}")
    left, right = line.rsplit("->", 1)
    return left.strip(), right.strip()


def load_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_id = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            if current_id is not None:
                sections.append((current_id, current_lines))
            current_id = line[1:-1].strip()
            current_lines = []
            continue
        if current_id is None:
            raise ValueError(f"Content found before any section header: {line}")
        current_lines.append(line)

    if current_id is not None:
        sections.append((current_id, current_lines))

    return sections


def parse_playbook(text: str) -> Graph:
    graph = Graph()

    for node_id, content_lines in load_sections(text):
        if not content_lines:
            raise ValueError(f"Section {node_id} is empty")

        first_line = content_lines[0]
        if first_line[:1].isdigit():
            graph.add_node(Node(id=node_id, text="", speaker="", type="choice"))
            for content_line in content_lines:
                edge_text, target = split_transition(content_line)
                graph.add_edge(Edge(source=node_id, target=target, text=edge_text))
            continue

        text_part, target = split_transition(first_line)
        if ":" not in text_part:
            raise ValueError(f"Dialogue line missing speaker separator in section {node_id}: {first_line}")
        speaker, spoken_text = text_part.split(":", 1)
        graph.add_node(Node(id=node_id, text=spoken_text.strip(), speaker=speaker.strip(), type="line"))
        graph.add_edge(Edge(source=node_id, target=target, text=""))

    errors = graph.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return graph


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def write_dot(graph: Graph, output_path: str) -> None:
    lines = [
        "digraph DrillPlaybook {",
        "  rankdir=TB;",
        "  node [fontname=\"Arial\", fontsize=10];",
        "  edge [fontname=\"Arial\", fontsize=8];",
        "  \"End\" [label=\"END\", shape=doublecircle, style=filled, fillcolor=lightgray];",
    ]

    for node in graph.nodes.values():
        if node.type == "choice":
            lines.append(
                f"  \"{escape_dot(node.id)}\" [label=\"{escape_dot(node.id)}\", shape=diamond, style=filled, fillcolor=lightblue];"
            )
        else:
            label = f"{node.id}\\n{node.speaker}: {node.text}"
            lines.append(
                f"  \"{escape_dot(node.id)}\" [label=\"{escape_dot(label)}\", shape=box, style=\"filled,rounded\", fillcolor=white];"
            )

    for edge in graph.edges:
        parts = [f"  \"{escape_dot(edge.source)}\" -> \"{escape_dot(edge.target)}\""]
        if edge.text:
            parts.append(f"[label=\"{escape_dot(edge.text)}\"]")
        lines.append(" ".join(parts) + ";")

    lines.append("}")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> None:
    input_path = find_input_path()
    output_dir = "/app" if os.path.isdir("/app") and input_path.startswith("/app/") else os.getcwd()
    json_path = os.path.join(output_dir, "drill_playbook_graph.json")
    dot_path = os.path.join(output_dir, "drill_playbook_graph.dot")

    with open(input_path, "r", encoding="utf-8") as handle:
        graph = parse_playbook(handle.read())

    with open(json_path, "w", encoding="utf-8") as handle:
        handle.write(graph.to_json())

    write_dot(graph, dot_path)

    print(f"Wrote {json_path} and {dot_path}")


if __name__ == "__main__":
    main()
PY
