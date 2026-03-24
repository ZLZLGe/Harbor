import os
import re
import json
import shutil
import sys

sys.path.append("/app/environment/skills/dialogue_graph/scripts")
sys.path.append("environment/skills/dialogue_graph/scripts")

from dialogue_graph import Edge, Graph, Node


def parse_script(text: str):
    graph = Graph()
    current_node_id = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        header_match = re.match(r"^\[(.*?)\]$", line)
        if header_match:
            current_node_id = header_match.group(1)
            if current_node_id not in graph.nodes:
                graph.add_node(Node(id=current_node_id, text="", speaker="", type="line"))
            continue

        if not current_node_id:
            continue

        node = graph.nodes[current_node_id]
        if "->" in line:
            text_part, target = [part.strip() for part in line.rsplit("->", 1)]
        else:
            text_part, target = line, None

        choice_match = re.match(r"^(\d+)\.\s*(.+)$", text_part)
        if choice_match:
            node.type = "choice"
            node.text = ""
            node.speaker = ""
            if target:
                graph.add_edge(Edge(source=current_node_id, target=target, text=text_part))
            continue

        if ":" in text_part:
            speaker, text_value = [part.strip() for part in text_part.split(":", 1)]
            node.type = "line"
            node.speaker = speaker
            node.text = text_value
            if target:
                graph.add_edge(Edge(source=current_node_id, target=target, text=""))
            continue

        node.type = "line"
        node.text = text_part
        if target:
            graph.add_edge(Edge(source=current_node_id, target=target, text=""))

    return graph


def write_dot(graph: Graph, path: str) -> None:
    speaker_colors = {
        "Narrator": "lightyellow",
        "Mira": "peachpuff",
        "Broker": "lightgreen",
        "Apprentice": "lightcyan",
        "Guard": "lightcoral",
    }

    def esc(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")

    lines = [
        "digraph DialogueGraph {",
        '  rankdir=TB;',
        '  splines=ortho;',
        '  node [fontname="Arial", fontsize="10"];',
        '  edge [fontname="Arial", fontsize="8"];',
    ]

    for node_id, node in graph.nodes.items():
        if node.type == "choice":
            lines.append(
                f'  "{esc(node_id)}" [label="{esc(node_id)}", shape=diamond, style=filled, fillcolor="lightblue"];'
            )
            continue

        if node.speaker and node.text:
            label = f"{node_id}\\n{node.speaker}: {node.text}"
        elif node.speaker:
            label = f"{node_id}\\n{node.speaker}"
        else:
            label = node_id
        fill = speaker_colors.get(node.speaker, "white")
        lines.append(
            f'  "{esc(node_id)}" [label="{esc(label)}", shape=box, style="filled,rounded", fillcolor="{fill}"];'
        )

    lines.append('  "End" [label="END", shape=doublecircle, style=filled, fillcolor="lightgray"];')

    for edge in graph.edges:
        attrs = []
        if edge.text:
            attrs.append(f'label="{esc(edge.text)}"')
            if "[" in edge.text and "]" in edge.text:
                attrs.append('color="darkblue"')
                attrs.append('fontcolor="darkblue"')
                attrs.append('style=bold')
            else:
                attrs.append('color="gray40"')
                attrs.append('fontcolor="gray40"')
        else:
            attrs.append('color="black"')
        lines.append(
            f'  "{esc(edge.source)}" -> "{esc(edge.target)}" [{", ".join(attrs)}];'
        )

    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    workdir = "/app" if os.path.exists("/app") else "."
    script_candidates = [
        os.path.join(workdir, "moon_market_script.txt"),
        "moon_market_script.txt",
        os.path.join("environment", "moon_market_script.txt"),
    ]
    script_path = next((candidate for candidate in script_candidates if os.path.exists(candidate)), script_candidates[0])
    output_json_path = os.path.join(workdir, "moon_market_graph.json")
    dot_base_path = os.path.join(workdir, "moon_market_graph")
    dot_output_path = dot_base_path + ".dot"

    with open(script_path, "r", encoding="utf-8") as f:
        graph = parse_script(f.read())

    validation_errors = graph.validate()
    if validation_errors:
        print("Validation warnings:")
        for error in validation_errors:
            print(f"  - {error}")

    with open(output_json_path, "w", encoding="utf-8") as f:
        f.write(graph.to_json())

    try:
        rendered_path = graph.visualize(dot_base_path, format="dot")
        if rendered_path != dot_output_path and os.path.exists(rendered_path) and not os.path.exists(dot_output_path):
            shutil.copyfile(rendered_path, dot_output_path)
    except Exception:
        write_dot(graph, dot_output_path)

    if not os.path.exists(dot_output_path):
        write_dot(graph, dot_output_path)

    print(json.dumps({"nodes": len(graph.nodes), "edges": len(graph.edges)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
