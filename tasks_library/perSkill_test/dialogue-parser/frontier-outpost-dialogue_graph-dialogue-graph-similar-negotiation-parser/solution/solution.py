import json
import os
import re
import sys
from collections import deque
from pathlib import Path


HERE = Path(__file__).resolve().parent
TASK_ROOT = HERE.parent

for skill_path in [
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.codex/skills/dialogue_graph/scripts",
    "/root/.claude/skills/dialogue_graph/scripts",
    "/root/.agents/skills/dialogue_graph/scripts",
    str(TASK_ROOT / "environment" / "skills" / "dialogue_graph" / "scripts"),
    "environment/skills/dialogue_graph/scripts",
]:
    if os.path.exists(skill_path):
        sys.path.insert(0, skill_path)

from dialogue_graph import Edge, Graph, Node


HEADER_RE = re.compile(r"^\[(?P<node_id>[^\]]+)\]$")
CHOICE_RE = re.compile(r"^(?P<label>\d+\.\s+.+?)\s*->\s*(?P<target>\S+)\s*$")
LINE_RE = re.compile(r"^(?P<speaker>[^:]+):\s*(?P<text>.+?)\s*->\s*(?P<target>\S+)\s*$")


def _parse_sections(text: str) -> tuple[list[str], dict[str, list[str]]]:
    order: list[str] = []
    sections: dict[str, list[str]] = {}
    current_node_id: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        header_match = HEADER_RE.match(line)
        if header_match:
            current_node_id = header_match.group("node_id")
            if current_node_id in sections:
                raise ValueError(f"Duplicate section header: {current_node_id}")
            order.append(current_node_id)
            sections[current_node_id] = []
            continue

        if current_node_id is None:
            raise ValueError(f"Found content before any section header: {line}")

        sections[current_node_id].append(line)

    if not order:
        raise ValueError("Script does not contain any section headers")

    return order, sections


def _build_graph(text: str) -> tuple[Graph, list[str]]:
    order, sections = _parse_sections(text)
    graph = Graph()

    for node_id in order:
        graph.add_node(Node(id=node_id, text="", speaker="", type="line"))

    for node_id in order:
        entries = sections[node_id]
        if not entries:
            raise ValueError(f"Section '{node_id}' is empty")

        node = graph.nodes[node_id]
        choice_matches = [CHOICE_RE.match(entry) for entry in entries]
        if all(choice_matches):
            node.type = "choice"
            node.text = ""
            node.speaker = ""
            for match in choice_matches:
                assert match is not None
                graph.add_edge(
                    Edge(
                        source=node_id,
                        target=match.group("target"),
                        text=match.group("label"),
                    )
                )
            continue

        if len(entries) != 1:
            raise ValueError(
                f"Section '{node_id}' must contain exactly one dialogue line or only numbered options"
            )

        line_match = LINE_RE.match(entries[0])
        if not line_match:
            raise ValueError(f"Section '{node_id}' has invalid entry: {entries[0]}")

        node.type = "line"
        node.speaker = line_match.group("speaker").strip()
        node.text = line_match.group("text").strip()
        graph.add_edge(Edge(source=node_id, target=line_match.group("target"), text=""))

    validation_errors = graph.validate()
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    reachable: set[str] = set()
    queue: deque[str] = deque([order[0]])
    adjacency: dict[str, list[str]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.source, []).append(edge.target)

    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        for target in adjacency.get(current, []):
            if target != "End":
                queue.append(target)

    unreachable = [node_id for node_id in order if node_id not in reachable]
    if unreachable:
        raise ValueError(f"Unreachable nodes: {', '.join(unreachable)}")

    return graph, order


def parse_script(text: str):
    graph, _ = _build_graph(text)
    return graph.to_dict()


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _write_dot(graph: Graph, order: list[str], output_path: str) -> None:
    lines = [
        "digraph OutpostDialogue {",
        '  rankdir=LR;',
        '  End [shape=doublecircle, label="End"];',
    ]

    for node_id in order:
        node = graph.nodes[node_id]
        shape = "diamond" if node.type == "choice" else "box"
        lines.append(f'  "{_escape_dot(node_id)}" [shape={shape}, label="{_escape_dot(node_id)}"];')

    for edge in graph.edges:
        attrs = ""
        if edge.text:
            attrs = f' [label="{_escape_dot(edge.text)}"]'
        lines.append(
            f'  "{_escape_dot(edge.source)}" -> "{_escape_dot(edge.target)}"{attrs};'
        )

    lines.append("}")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> None:
    workdir = "/app" if os.path.exists("/app") else os.getcwd()
    script_path = os.path.join(workdir, "outpost_script.txt")
    json_path = os.path.join(workdir, "outpost_dialogue.json")
    dot_path = os.path.join(workdir, "outpost_dialogue.dot")

    if not os.path.exists(script_path):
        fallback_script = "outpost_script.txt"
        if os.path.exists(fallback_script):
            script_path = fallback_script
            json_path = "outpost_dialogue.json"
            dot_path = "outpost_dialogue.dot"
        else:
            raise FileNotFoundError("Could not find outpost_script.txt")

    with open(script_path, "r", encoding="utf-8") as handle:
        script_text = handle.read()

    graph, order = _build_graph(script_text)

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(graph.to_dict(), handle, indent=2)
        handle.write("\n")

    _write_dot(graph, order, dot_path)


if __name__ == "__main__":
    main()
