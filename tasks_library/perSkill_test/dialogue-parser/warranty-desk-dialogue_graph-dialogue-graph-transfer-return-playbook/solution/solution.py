import json
import os
import re
import sys


for skill_path in [
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.codex/skills/dialogue_graph/scripts",
    "/root/.claude/skills/dialogue_graph/scripts",
    "environment/skills/dialogue_graph/scripts",
]:
    if os.path.exists(skill_path):
        sys.path.insert(0, skill_path)
        break


from dialogue_graph import Edge, Graph, Node


HEADER_RE = re.compile(r"^\[(?P<node_id>[A-Za-z0-9_]+)\]$")
CHOICE_RE = re.compile(r"^\d+\.\s+.+$")


def parse_script(text: str):
    graph = Graph()
    current_node_id = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        header_match = HEADER_RE.match(line)
        if header_match:
            current_node_id = header_match.group("node_id")
            if current_node_id not in graph.nodes:
                graph.add_node(Node(id=current_node_id, text="", speaker="", type="line"))
            continue

        if current_node_id is None:
            continue

        node = graph.nodes[current_node_id]
        text_part, target = _split_transition(line)

        if CHOICE_RE.match(text_part):
            node.type = "choice"
            node.text = ""
            node.speaker = ""
            if target:
                graph.add_edge(Edge(source=current_node_id, target=target, text=text_part))
            continue

        if ":" in text_part:
            speaker, spoken_text = text_part.split(":", 1)
            node.type = "line"
            node.speaker = speaker.strip()
            node.text = spoken_text.strip()
            if target:
                graph.add_edge(Edge(source=current_node_id, target=target, text=""))
            continue

        node.type = "line"
        node.text = text_part
        if target:
            graph.add_edge(Edge(source=current_node_id, target=target, text=""))

    return graph


def _split_transition(line: str):
    if "->" not in line:
        return line.strip(), None
    text_part, target = line.rsplit("->", 1)
    return text_part.strip(), target.strip()


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _write_fallback_dot(graph: Graph, output_path: str):
    speaker_colors = {
        "Narrator": "lightyellow",
        "Guard": "lightcoral",
        "Stranger": "plum",
        "Merchant": "lightgreen",
        "Barkeep": "peachpuff",
        "Kira": "lightcyan",
    }

    lines = [
        "digraph G {",
        '  graph [rankdir=TB, splines=ortho, nodesep="0.5", ranksep="0.8"];',
        '  node [fontname="Arial", fontsize="10"];',
        '  edge [fontname="Arial", fontsize="8"];',
    ]

    for node_id, node in graph.nodes.items():
        if node.type == "choice":
            lines.append(
                f'  "{_escape_dot(node_id)}" [label="{_escape_dot(node_id)}", shape=diamond, style=filled, fillcolor=lightblue, width="1.5"];'
            )
            continue

        text = node.text[:37] + "..." if len(node.text) > 40 else node.text
        if node.speaker and text:
            label = f"{node_id}\\n{node.speaker}: {text}"
        elif node.speaker:
            label = f"{node_id}\\n{node.speaker}"
        else:
            label = node_id
        color = speaker_colors.get(node.speaker, "white")
        lines.append(
            f'  "{_escape_dot(node_id)}" [label="{_escape_dot(label)}", shape=box, style="filled,rounded", fillcolor="{_escape_dot(color)}", width="2"];'
        )

    lines.append('  "End" [label="END", shape=doublecircle, style=filled, fillcolor=lightgray, width="0.8"];')

    for edge in graph.edges:
        attributes = ['color="black"']
        edge_text = edge.text[:27] + "..." if len(edge.text) > 30 else edge.text
        if edge_text:
            if "[" in edge_text and "]" in edge_text:
                attributes = [
                    f'label="{_escape_dot(edge_text)}"',
                    'color="darkblue"',
                    'fontcolor="darkblue"',
                    'style=bold',
                ]
            else:
                attributes = [
                    f'label="{_escape_dot(edge_text)}"',
                    'color="gray40"',
                    'fontcolor="gray40"',
                ]
        lines.append(
            f'  "{_escape_dot(edge.source)}" -> "{_escape_dot(edge.target)}" [{", ".join(attributes)}];'
        )

    lines.append("}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    workdir = "/app" if os.path.exists("/app") else os.getcwd()
    input_path = os.path.join(workdir, "return_playbook.txt")
    output_json_path = os.path.join(workdir, "warranty_returns_flow.json")
    output_base_path = os.path.join(workdir, "warranty_returns_flow")

    if not os.path.exists(input_path):
        local_input_candidates = [
            "return_playbook.txt",
            os.path.join("environment", "return_playbook.txt"),
        ]
        for candidate in local_input_candidates:
            if os.path.exists(candidate):
                input_path = candidate
                break
        output_json_path = "warranty_returns_flow.json"
        output_base_path = "warranty_returns_flow"

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    graph = parse_script(text)

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2)

    try:
        graph.visualize(output_base_path, format="dot")
    except Exception:
        _write_fallback_dot(graph, f"{output_base_path}.dot")

    errors = graph.validate()
    if errors:
        print("Validation warnings:")
        for error in errors:
            print(f"- {error}")

    print(f"Generated {output_json_path} with {len(graph.nodes)} nodes and {len(graph.edges)} edges")


if __name__ == "__main__":
    main()
