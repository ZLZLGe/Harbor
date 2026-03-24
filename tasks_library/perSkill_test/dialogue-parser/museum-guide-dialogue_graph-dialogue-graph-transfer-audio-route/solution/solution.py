import json
import os
import re
import sys

for skill_path in [
    "environment/skills/dialogue_graph/scripts",
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.codex/skills/dialogue_graph/scripts",
]:
    if os.path.exists(skill_path):
        sys.path.append(skill_path)
        break

from dialogue_graph import Edge, Graph, Node


def parse_script(text: str):
    graph = Graph()
    current_node_id = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = re.match(r"^\[(.+?)\]$", line)
        if header_match:
            current_node_id = header_match.group(1)
            if current_node_id not in graph.nodes:
                graph.add_node(Node(id=current_node_id, text="", speaker="", type="line"))
            continue

        if current_node_id is None:
            continue

        node = graph.nodes[current_node_id]

        if "->" in line:
            text_part, target = line.rsplit("->", 1)
            text_part = text_part.strip()
            target = target.strip()
        else:
            text_part = line
            target = ""

        choice_match = re.match(r"^\d+\.\s+.+$", text_part)
        if choice_match:
            node.type = "choice"
            node.text = ""
            node.speaker = ""
            graph.add_edge(Edge(source=current_node_id, target=target, text=text_part))
            continue

        if ":" in text_part:
            speaker, spoken_text = text_part.split(":", 1)
            node.type = "line"
            node.speaker = speaker.strip()
            node.text = spoken_text.strip()
            if target:
                graph.add_edge(Edge(source=current_node_id, target=target, text=""))

    return graph


def dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\"", "\\\"")


def write_dot(graph: Graph, path: str):
    speaker_colors = {
        "Guide": "lightyellow",
        "Curator": "lightcyan",
        "PaleoHost": "wheat",
        "MarineHost": "lightblue",
        "InnovationHost": "honeydew",
        "AccessibilityHost": "lavender",
        "FamilyGuide": "mistyrose",
        "Archivist": "oldlace",
        "Conservator": "azure",
        "Narrator": "white",
    }

    lines = [
        "digraph MuseumRoute {",
        '  rankdir=TB;',
        '  splines=ortho;',
        '  node [fontname="Arial", fontsize="10"];',
        '  edge [fontname="Arial", fontsize="8"];',
    ]

    for node in graph.nodes.values():
        if node.type == "choice":
            lines.append(
                f'  "{dot_escape(node.id)}" [label="{dot_escape(node.id)}", shape=diamond, style=filled, fillcolor="lightblue"];'
            )
            continue

        text = node.text[:40] + "..." if len(node.text) > 43 else node.text
        if node.speaker and text:
            label = f"{node.id}\\n{node.speaker}: {text}"
        elif node.speaker:
            label = f"{node.id}\\n{node.speaker}"
        else:
            label = node.id
        fillcolor = speaker_colors.get(node.speaker, "white")
        lines.append(
            f'  "{dot_escape(node.id)}" [label="{dot_escape(label)}", shape=box, style="filled,rounded", fillcolor="{fillcolor}"];'
        )

    lines.append('  "End" [label="END", shape=doublecircle, style=filled, fillcolor="lightgray"];')

    for edge in graph.edges:
        attributes = []
        if edge.text:
            attributes.append(f'label="{dot_escape(edge.text)}"')
            if "[" in edge.text and "]" in edge.text:
                attributes.append('color="darkblue"')
                attributes.append('fontcolor="darkblue"')
                attributes.append('style=bold')
            else:
                attributes.append('color="gray40"')
                attributes.append('fontcolor="gray40"')
        else:
            attributes.append('color="black"')

        lines.append(
            f'  "{dot_escape(edge.source)}" -> "{dot_escape(edge.target)}" [{", ".join(attributes)}];'
        )

    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    input_candidates = [
        "/app/museum_audio_script.txt",
        "museum_audio_script.txt",
        "environment/museum_audio_script.txt",
    ]
    input_path = next(path for path in input_candidates if os.path.exists(path))

    output_dir = "/app" if os.path.exists("/app") else "."
    json_path = os.path.join(output_dir, "museum_audio_route.json")
    dot_base = os.path.join(output_dir, "museum_audio_route")

    with open(input_path, "r", encoding="utf-8") as f:
        graph = parse_script(f.read())

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(graph.to_json())

    write_dot(graph, dot_base + ".dot")

    errors = graph.validate()
    if errors:
        raise ValueError("\n".join(errors))

    print(json.dumps({"nodes": len(graph.nodes), "edges": len(graph.edges)}))


if __name__ == "__main__":
    main()
