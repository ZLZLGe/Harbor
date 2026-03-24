import os
import re
import sys
from collections import deque

for candidate in [
    "/app/environment/skills/dialogue_graph/scripts",
    "environment/skills/dialogue_graph/scripts",
]:
    if os.path.exists(candidate):
        sys.path.append(candidate)

from dialogue_graph import Edge, Graph, Node


def parse_script(text: str):
    graph = build_graph(text)
    return graph.to_dict()


def build_graph(text: str) -> Graph:
    graph = Graph()
    current_id = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        header_match = re.match(r"^\[(.+?)\]$", line)
        if header_match:
            current_id = header_match.group(1)
            if current_id not in graph.nodes:
                graph.add_node(Node(id=current_id, text="", speaker="", type="line"))
            continue

        if current_id is None:
            continue

        node = graph.nodes[current_id]
        text_part = line
        target = None
        if "->" in line:
            text_part, target = [part.strip() for part in line.rsplit("->", 1)]

        if re.match(r"^\d+\.\s+.+$", text_part):
            node.type = "choice"
            node.text = ""
            node.speaker = ""
            if target:
                graph.add_edge(Edge(source=current_id, target=target, text=text_part))
            continue

        speaker_match = re.match(r"^([^:]+):\s*(.+)$", text_part)
        if speaker_match:
            node.type = "line"
            node.speaker = speaker_match.group(1).strip()
            node.text = speaker_match.group(2).strip()
            if target:
                graph.add_edge(Edge(source=current_id, target=target, text=""))
            continue

        node.type = "line"
        node.text = text_part
        node.speaker = ""
        if target:
            graph.add_edge(Edge(source=current_id, target=target, text=""))

    return graph


def validate_graph(graph: Graph) -> None:
    errors = list(graph.validate())
    if "Start" not in graph.nodes:
        errors.append("Missing Start node")

    edge_map = {}
    for edge in graph.edges:
        edge_map.setdefault(edge.source, []).append(edge.target)

    if "Start" in graph.nodes:
        reachable = set()
        queue = deque(["Start"])
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for target in edge_map.get(current, []):
                if target != "End":
                    queue.append(target)

        unreachable = sorted(set(graph.nodes) - reachable)
        if unreachable:
            errors.append(f"Unreachable nodes: {', '.join(unreachable)}")

    if errors:
        raise SystemExit("\n".join(errors))


def write_dot(graph: Graph, output_path: str) -> None:
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\"", "\\\"")

    lines = [
        "digraph EvacuationResponse {",
        '  rankdir=TB;',
        '  node [fontname="Arial", fontsize="10"];',
        '  edge [fontname="Arial", fontsize="8"];',
        '  End [label="END", shape=doublecircle, style=filled, fillcolor="lightgray"];',
    ]

    for node in graph.nodes.values():
        if node.type == "choice":
            lines.append(
                f'  "{escape(node.id)}" [label="{escape(node.id)}", shape=diamond, style=filled, fillcolor="lightblue"];'
            )
            continue

        label = node.id
        if node.speaker and node.text:
            label = f"{node.id}\\n{node.speaker}: {node.text}"
        elif node.speaker:
            label = f"{node.id}\\n{node.speaker}"
        elif node.text:
            label = f"{node.id}\\n{node.text}"
        lines.append(
            f'  "{escape(node.id)}" [label="{escape(label)}", shape=box, style="filled,rounded", fillcolor="white"];'
        )

    for edge in graph.edges:
        if edge.text:
            lines.append(
                f'  "{escape(edge.source)}" -> "{escape(edge.target)}" [label="{escape(edge.text)}"];'
            )
        else:
            lines.append(f'  "{escape(edge.source)}" -> "{escape(edge.target)}";')

    lines.append("}")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> None:
    if os.path.exists("/app/evacuation_drill_script.txt"):
        base_dir = "/app"
        script_path = "/app/evacuation_drill_script.txt"
    else:
        base_dir = "."
        script_path = os.path.join("environment", "evacuation_drill_script.txt")

    json_path = os.path.join(base_dir, "evacuation_response.json")
    dot_path = os.path.join(base_dir, "evacuation_response.dot")

    with open(script_path, "r", encoding="utf-8") as handle:
        text = handle.read()

    graph = build_graph(text)
    validate_graph(graph)

    with open(json_path, "w", encoding="utf-8") as handle:
        handle.write(graph.to_json())

    write_dot(graph, dot_path)


if __name__ == "__main__":
    main()
