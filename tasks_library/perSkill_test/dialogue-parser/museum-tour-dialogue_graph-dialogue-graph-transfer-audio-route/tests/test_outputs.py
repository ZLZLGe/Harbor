import glob
import json
import os
import re
import sys
from collections import deque

import pytest

for skill_path in [
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.claude/skills/dialogue_graph/scripts",
    "/root/.agents/skills/dialogue_graph/scripts",
    "environment/skills/dialogue_graph/scripts",
]:
    if os.path.exists(skill_path):
        sys.path.insert(0, skill_path)
        break


@pytest.fixture(scope="module")
def route_data():
    direct_paths = [
        "/app/museum_route.json",
        "museum_route.json",
        "/root/museum_route.json",
    ]
    for path in direct_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)

    for pattern in ["/app/**/museum_route.json", "/root/**/museum_route.json", "./**/museum_route.json"]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            with open(matches[0], "r", encoding="utf-8") as handle:
                return json.load(handle)

    pytest.fail("museum_route.json not found in expected locations")


@pytest.fixture(scope="module")
def nodes(route_data):
    return {node["id"]: node for node in route_data["nodes"]}


@pytest.fixture(scope="module")
def edges(route_data):
    return route_data["edges"]


@pytest.fixture(scope="module")
def edge_map(edges):
    mapping = {}
    for edge in edges:
        mapping.setdefault(edge["from"], []).append(edge["to"])
    return mapping


@pytest.fixture(scope="module")
def dot_content():
    for path in ["/app/museum_route.dot", "museum_route.dot", "/root/museum_route.dot"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
    return None


@pytest.mark.parametrize("check", ["json_structure", "schema", "dot_exists", "graph_size"])
def test_system_basics(route_data, nodes, edges, dot_content, check):
    if check == "json_structure":
        assert "nodes" in route_data, "Missing 'nodes' key in museum_route.json"
        assert "edges" in route_data, "Missing 'edges' key in museum_route.json"
        assert isinstance(route_data["nodes"], list), "'nodes' should be a list"
        assert isinstance(route_data["edges"], list), "'edges' should be a list"

    elif check == "schema":
        for node in route_data["nodes"]:
            assert isinstance(node.get("id"), str) and node["id"], f"Invalid node id: {node}"
            assert isinstance(node.get("text"), str), f"Node {node.get('id')} missing valid text"
            assert isinstance(node.get("speaker"), str), f"Node {node.get('id')} missing valid speaker"
            assert node.get("type") in {"line", "choice"}, f"Node {node.get('id')} has invalid type"

        for edge in route_data["edges"]:
            assert isinstance(edge.get("from"), str) and edge["from"], f"Invalid edge source: {edge}"
            assert isinstance(edge.get("to"), str) and edge["to"], f"Invalid edge target: {edge}"
            assert isinstance(edge.get("text"), str), f"Edge missing valid text: {edge}"

    elif check == "dot_exists":
        assert dot_content is not None, "museum_route.dot visualization file missing"

    elif check == "graph_size":
        assert len(nodes) >= 55, f"Expected at least 55 nodes, got {len(nodes)}"
        assert len(edges) >= 70, f"Expected at least 70 edges, got {len(edges)}"


@pytest.mark.parametrize("category,expected_value", [
    ("speaker", "Guide"),
    ("speaker", "Curator"),
    ("speaker", "Conservator"),
    ("speaker", "Access Host"),
    ("node", "Start"),
    ("node", "OrientationHub"),
    ("node", "AccessibilityChoice"),
    ("node", "CrossWingChoice"),
    ("node", "ReplayChoice"),
])
def test_route_content(nodes, category, expected_value):
    if category == "speaker":
        speakers = {node["speaker"] for node in nodes.values() if node.get("speaker")}
        assert expected_value in speakers, f"Missing required speaker '{expected_value}'"
    else:
        assert expected_value in nodes, f"Missing required node '{expected_value}'"


@pytest.mark.parametrize("logic_check", ["edges_valid", "reachability", "multiple_endings", "choice_hubs", "cross_wing_loops"])
def test_graph_logic(nodes, edges, edge_map, logic_check):
    if logic_check == "edges_valid":
        for edge in edges:
            assert edge["from"] in nodes, f"Edge source '{edge['from']}' missing"
            if edge["to"] != "End":
                assert edge["to"] in nodes, f"Edge target '{edge['to']}' missing"

    elif logic_check == "reachability":
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

        unreachable = set(nodes) - reachable
        assert not unreachable, f"Unreachable nodes found: {sorted(unreachable)[:5]}"

    elif logic_check == "multiple_endings":
        ending_edges = [edge for edge in edges if edge["to"] == "End"]
        assert len(ending_edges) >= 4, f"Expected at least 4 endings, got {len(ending_edges)}"

    elif logic_check == "choice_hubs":
        assert len(edge_map.get("OrientationHub", [])) == 4, "OrientationHub should have 4 options"
        assert len(edge_map.get("AccessibilityChoice", [])) == 4, "AccessibilityChoice should have 4 options"
        assert len(edge_map.get("ReplayChoice", [])) == 4, "ReplayChoice should have 4 options"

    elif logic_check == "cross_wing_loops":
        assert "CrossWingChoice" in edge_map.get("TradeRoute", []), "TradeRoute should feed CrossWingChoice"
        assert "CrossWingChoice" in edge_map.get("TradeMap", []), "TradeMap should feed CrossWingChoice"
        assert "AccessibilityIntro" in edge_map.get("EthicsNote", []), "EthicsNote should redirect to accessibility"
        assert "FossilIntro" in edge_map.get("FootprintHunt", []), "FootprintHunt should loop back to fossils"
        assert "MaritimeIntro" in edge_map.get("MaritimeBypass", []), "MaritimeBypass should re-enter maritime intro"


@pytest.mark.parametrize("check_type,identifier,fragment", [
    ("node_text", "DinoNarration", "Notice the healed fracture on the mammoth rib"),
    ("node_text", "EthicsNote", "we do not repaint history into something neater than it ever was"),
    ("node_text", "TranscriptSent", "includes captions for every ambient audio segment"),
    ("edge_text", "AccessibilityChoice", "[Quiet Route] Build a low-noise path."),
    ("edge_text", "AccessibilityChoice", "[Family] Start the scavenger prompts."),
    ("edge_text", "SupportChoice", "1. Send the QR transcript now."),
    ("node_id", "LoopGallery", None),
    ("node_id", "SculptureChoice", None),
    ("dynamic_script_sample", "museum_audio_route.txt", None),
    ("first_node_check", "museum_audio_route.txt", None),
])
def test_content_integrity(nodes, edges, check_type, identifier, fragment):
    if check_type == "node_id":
        assert identifier in nodes, f"Specific node '{identifier}' from input script missing"

    elif check_type == "node_text":
        assert identifier in nodes, f"Node '{identifier}' missing"
        assert fragment in nodes[identifier]["text"], f"Node '{identifier}' text mismatch"

    elif check_type == "edge_text":
        assert any(edge["from"] == identifier and fragment in edge["text"] for edge in edges), (
            f"Edge from '{identifier}' with text '{fragment}' missing"
        )

    elif check_type == "dynamic_script_sample":
        if os.path.exists("/app/museum_audio_route.txt"):
            script_path = "/app/museum_audio_route.txt"
        elif os.path.exists("museum_audio_route.txt"):
            script_path = "museum_audio_route.txt"
        else:
            script_path = "environment/museum_audio_route.txt"
        with open(script_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        matches = re.findall(r"^([A-Za-z][A-Za-z ]+):\s+([^\[\n]+?)\s+->\s+([A-Za-z]+)$", content, re.MULTILINE)
        assert matches, "Could not sample standard dialogue lines from museum_audio_route.txt"

        for index, (speaker, text, _target) in enumerate(matches):
            if index % 4 != 0:
                continue
            found = any(
                node.get("speaker") == speaker and text.strip() in node.get("text", "")
                for node in nodes.values()
            )
            assert found, f"Sampled script line not found in graph: {speaker}: {text}"

    elif check_type == "first_node_check":
        if os.path.exists("/app/museum_audio_route.txt"):
            script_path = "/app/museum_audio_route.txt"
        elif os.path.exists("museum_audio_route.txt"):
            script_path = "museum_audio_route.txt"
        else:
            script_path = "environment/museum_audio_route.txt"
        with open(script_path, "r", encoding="utf-8") as handle:
            first_header = next((line for line in handle if line.strip().startswith("[")), None)

        assert first_header, "Script has no section headers"
        match = re.match(r"^\[(.*?)\]", first_header.strip())
        assert match, "Could not parse first section header"
        assert match.group(1) == "Start", f"Expected first section to be Start, got {match.group(1)}"
        assert "Start" in nodes, "First node 'Start' missing from output graph"


@pytest.mark.parametrize("source,target", [
    ("Start", "OrientationHub"),
    ("OrientationHub", "FossilIntro"),
    ("OrientationHub", "AccessibilityIntro"),
    ("FossilChoice", "TimelineBridge"),
    ("TradeRoute", "CrossWingChoice"),
    ("CaptainChoice", "SailRepair"),
    ("LabChoice", "ConservatorIntro"),
    ("QuietChoice", "SculptureCourt"),
    ("SupportChoice", "TranscriptSent"),
    ("EchoReturn", "ReplayChoice"),
])
def test_structural_integrity(nodes, edge_map, source, target):
    assert source in nodes, f"Source '{source}' missing"
    assert target in nodes, f"Target '{target}' missing"
    assert target in edge_map.get(source, []), f"Expected connection {source} -> {target} missing"


@pytest.mark.parametrize("viz_check", ["header", "syntax", "diamonds", "content"])
def test_visualization(dot_content, viz_check):
    if dot_content is None:
        pytest.skip("DOT file missing")

    if viz_check == "header":
        assert "digraph" in dot_content, "DOT must use 'digraph'"
    elif viz_check == "syntax":
        assert "{" in dot_content and "}" in dot_content, "DOT missing braces"
        assert "->" in dot_content, "DOT missing directed edges"
    elif viz_check == "diamonds":
        assert "shape=diamond" in dot_content or 'shape=\"diamond\"' in dot_content, (
            "Choice nodes should be visualized as diamonds"
        )
    elif viz_check == "content":
        assert "OrientationHub" in dot_content, "Visualization missing OrientationHub"
        assert "AccessibilityChoice" in dot_content, "Visualization missing AccessibilityChoice"
        assert "End" in dot_content, "Visualization missing End node"


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
