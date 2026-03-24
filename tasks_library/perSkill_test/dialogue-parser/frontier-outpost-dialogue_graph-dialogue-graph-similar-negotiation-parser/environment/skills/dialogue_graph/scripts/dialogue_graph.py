import json
from typing import Any, Dict, List


class Node:
    def __init__(self, id: str, text: str = "", speaker: str = "", type: str = "line"):
        self.id = id
        self.text = text
        self.speaker = speaker
        self.type = type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "speaker": self.speaker,
            "type": self.type,
        }


class Edge:
    def __init__(self, source: str, target: str, text: str = ""):
        self.source = source
        self.target = target
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {"from": self.source, "to": self.target, "text": self.text}


class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

    def add_node(self, node: Node):
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists")
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge):
        self.edges.append(edge)

    def validate(self) -> List[str]:
        errors = []
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"Edge source '{edge.source}' not found")
            if edge.target not in self.nodes and edge.target != "End":
                errors.append(f"Edge target '{edge.target}' not found")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Graph":
        graph = Graph()
        for node in data.get("nodes", []):
            graph.nodes[node["id"]] = Node(
                id=node["id"],
                text=node.get("text", ""),
                speaker=node.get("speaker", ""),
                type=node.get("type", "line"),
            )
        for edge in data.get("edges", []):
            graph.edges.append(
                Edge(
                    source=edge["from"],
                    target=edge["to"],
                    text=edge.get("text", ""),
                )
            )
        return graph
