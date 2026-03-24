import json
import os
import re
import sys


for skill_path in [
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.codex/skills/dialogue_graph/scripts",
    "/root/.claude/skills/dialogue_graph/scripts",
    "/root/.agents/skills/dialogue_graph/scripts",
    "environment/skills/dialogue_graph/scripts",
]:
    if skill_path not in sys.path:
        sys.path.append(skill_path)

from dialogue_graph import Edge, Graph, Node


HEADER_RE = re.compile(r"^\[(.+?)\]$")
CHOICE_RE = re.compile(r"^\d+\.\s+.+$")


def parse_script(text: str):
    graph = Graph()
    current_node_id = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("#", "-", ">", "//", "```")):
            continue

        header_match = HEADER_RE.match(line)
        if header_match:
            current_node_id = header_match.group(1)
            if current_node_id not in graph.nodes:
                graph.add_node(Node(id=current_node_id, text="", speaker="", type="line"))
            continue

        if current_node_id is None or "->" not in line:
            continue

        text_part, target = [part.strip() for part in line.rsplit("->", 1)]
        node = graph.nodes[current_node_id]

        if CHOICE_RE.match(text_part):
            node.type = "choice"
            node.text = ""
            node.speaker = ""
            graph.add_edge(Edge(source=current_node_id, target=target, text=text_part))
            continue

        if ":" not in text_part:
            continue

        speaker, text_value = [part.strip() for part in text_part.split(":", 1)]
        node.type = "line"
        node.speaker = speaker
        node.text = text_value
        graph.add_edge(Edge(source=current_node_id, target=target, text=""))

    return graph


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def write_dot(graph: Graph, output_path: str) -> None:
    speaker_colors = {
        "Monitor": "lightyellow",
        "IncidentLead": "mistyrose",
        "ReleaseEngineer": "lightcyan",
        "SRE": "honeydew",
        "Database": "lavender",
        "Comms": "peachpuff",
        "Observability": "lightgoldenrod1",
        "EdgeTeam": "aliceblue",
        "ServiceOwner": "azure",
        "SupportLead": "mintcream",
    }

    lines = [
        "digraph DialogueGraph {",
        '  rankdir="TB";',
        '  splines="ortho";',
        '  nodesep="0.5";',
        '  ranksep="0.8";',
        '  node [fontname="Arial" fontsize="10"];',
        '  edge [fontname="Arial" fontsize="8"];',
        '  "End" [label="END" shape="doublecircle" style="filled" fillcolor="lightgray" width="0.8"];',
    ]

    for node in graph.nodes.values():
        if node.type == "choice":
            lines.append(
                f'  "{escape_dot(node.id)}" [label="{escape_dot(node.id)}" shape="diamond" style="filled" fillcolor="lightblue" width="1.5"];'
            )
            continue

        label = node.id
        if node.speaker and node.text:
            label = f"{node.id}\\n{node.speaker}: {node.text}"
        elif node.speaker:
            label = f"{node.id}\\n{node.speaker}"

        fill = speaker_colors.get(node.speaker, "white")
        lines.append(
            f'  "{escape_dot(node.id)}" [label="{escape_dot(label)}" shape="box" style="filled,rounded" fillcolor="{fill}" width="2"];'
        )

    for edge in graph.edges:
        attrs = ['color="black"']
        if edge.text:
            attrs = ['label="' + escape_dot(edge.text) + '"']
            if "[" in edge.text and "]" in edge.text:
                attrs.extend(['color="darkblue"', 'fontcolor="darkblue"', 'style="bold"'])
            else:
                attrs.extend(['color="gray40"', 'fontcolor="gray40"'])
        lines.append(
            f'  "{escape_dot(edge.source)}" -> "{escape_dot(edge.target)}" [{ " ".join(attrs) }];'
        )

    lines.append("}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    workdir = "/app" if os.path.exists("/app") else "."
    input_path = os.path.join(workdir, "incident_triage_handbook.md")
    json_path = os.path.join(workdir, "incident_triage_map.json")
    dot_path = os.path.join(workdir, "incident_triage_map.dot")

    with open(input_path, "r", encoding="utf-8") as f:
        graph = parse_script(f.read())

    validation_errors = graph.validate()
    if validation_errors:
        raise ValueError("Graph validation failed: " + "; ".join(validation_errors))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2)

    write_dot(graph, dot_path)


if __name__ == "__main__":
    main()
