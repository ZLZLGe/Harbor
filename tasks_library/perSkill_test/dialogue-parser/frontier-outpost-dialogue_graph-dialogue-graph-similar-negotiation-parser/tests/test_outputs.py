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
def dialogue_data():
    direct_paths = [
        "/app/outpost_dialogue.json",
        "outpost_dialogue.json",
        "/root/outpost_dialogue.json",
    ]
    for path in direct_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)

    for pattern in ["/app/**/outpost_dialogue.json", "/root/**/outpost_dialogue.json", "./**/outpost_dialogue.json"]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            with open(matches[0], "r", encoding="utf-8") as handle:
                return json.load(handle)

    pytest.fail("outpost_dialogue.json not found in expected locations")


@pytest.fixture(scope="module")
def nodes(dialogue_data):
    return {node["id"]: node for node in dialogue_data["nodes"]}


@pytest.fixture(scope="module")
def edges(dialogue_data):
    return dialogue_data["edges"]


@pytest.fixture(scope="module")
def edge_map(edges):
    mapping = {}
    for edge in edges:
        mapping.setdefault(edge["from"], []).append(edge["to"])
    return mapping


@pytest.fixture(scope="module")
def dot_content():
    for path in ["/app/outpost_dialogue.dot", "outpost_dialogue.dot", "/root/outpost_dialogue.dot"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
    return None


@pytest.mark.parametrize("check", ["json_structure", "schema", "dot_exists", "graph_size"])
def test_system_basics(dialogue_data, nodes, edges, dot_content, check):
    if check == "json_structure":
        assert "nodes" in dialogue_data, "Missing 'nodes' key in outpost_dialogue.json"
        assert "edges" in dialogue_data, "Missing 'edges' key in outpost_dialogue.json"
        assert isinstance(dialogue_data["nodes"], list), "'nodes' should be a list"
        assert isinstance(dialogue_data["edges"], list), "'edges' should be a list"

    elif check == "schema":
        for node in dialogue_data["nodes"]:
            assert isinstance(node.get("id"), str) and node["id"], f"Invalid node id: {node}"
            assert isinstance(node.get("text"), str), f"Node {node.get('id')} missing valid text"
            assert isinstance(node.get("speaker"), str), f"Node {node.get('id')} missing valid speaker"
            assert node.get("type") in {"line", "choice"}, f"Node {node.get('id')} has invalid type"

        for edge in dialogue_data["edges"]:
            assert isinstance(edge.get("from"), str) and edge["from"], f"Invalid edge source: {edge}"
            assert isinstance(edge.get("to"), str) and edge["to"], f"Invalid edge target: {edge}"
            assert isinstance(edge.get("text"), str), f"Edge missing valid text: {edge}"

    elif check == "dot_exists":
        assert dot_content is not None, "outpost_dialogue.dot visualization file missing"

    elif check == "graph_size":
        assert len(nodes) >= 35, f"Expected at least 35 nodes, got {len(nodes)}"
        assert len(edges) >= 45, f"Expected at least 45 edges, got {len(edges)}"


@pytest.mark.parametrize("category,expected_value", [
    ("speaker", "Narrator"),
    ("speaker", "Commander Vela"),
    ("speaker", "Quartermaster Suri"),
    ("speaker", "Clerk Iven"),
    ("node", "Start"),
    ("node", "NegotiationHub"),
    ("node", "PassageTerms"),
    ("node", "ContractDecision"),
    ("node", "Detained"),
])
def test_narrative_content(nodes, category, expected_value):
    if category == "speaker":
        speakers = {node["speaker"] for node in nodes.values() if node.get("speaker")}
        assert expected_value in speakers, f"Missing required speaker '{expected_value}'"
    else:
        assert expected_value in nodes, f"Missing required node '{expected_value}'"


@pytest.mark.parametrize("logic_check", ["edges_valid", "reachability", "loopbacks", "multiple_endings", "choice_hubs"])
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

    elif logic_check == "loopbacks":
        back_to_hub = [edge for edge in edges if edge["to"] == "NegotiationHub"]
        assert len(back_to_hub) >= 8, f"Expected many loopbacks to NegotiationHub, got {len(back_to_hub)}"

    elif logic_check == "multiple_endings":
        ending_edges = [edge for edge in edges if edge["to"] == "End"]
        assert len(ending_edges) >= 5, f"Expected at least 5 endings, got {len(ending_edges)}"

    elif logic_check == "choice_hubs":
        assert len(edge_map.get("NegotiationHub", [])) == 4, "NegotiationHub should have 4 options"
        assert len(edge_map.get("CaravanChoice", [])) == 4, "CaravanChoice should have 4 options"
        assert len(edge_map.get("ContractChoice", [])) == 4, "ContractChoice should have 4 options"


@pytest.mark.parametrize("check_type,identifier,fragment", [
    ("node_text", "ScoutRead", "signal horn hangs unwatched beside the gate crank"),
    ("node_text", "FeeWaiver", "Waive the fee and the stores come out of my ledgers"),
    ("node_text", "ContractSealed", "sentries mark your name as trusted"),
    ("edge_text", "NegotiationHub", "Request emergency passage for a medical caravan."),
    ("edge_text", "CaravanChoice", "[Persuade] Describe the fever spreading beyond the ridge."),
    ("edge_text", "ContractDecision", "[Persuade] Ask for eight days because of the ice road."),
    ("node_id", "AlarmRaised", None),
    ("node_id", "TreatyWin", None),
    ("dynamic_script_sample", "outpost_script.txt", None),
    ("first_node_check", "outpost_script.txt", None),
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
        script_path = "/app/outpost_script.txt" if os.path.exists("/app/outpost_script.txt") else "outpost_script.txt"
        with open(script_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        matches = re.findall(r"^([A-Za-z][A-Za-z ]+):\s+([^\[\n]+?)\s+->\s+([A-Za-z]+)$", content, re.MULTILINE)
        assert matches, "Could not sample standard dialogue lines from outpost_script.txt"

        for index, (speaker, text, _target) in enumerate(matches):
            if index % 4 != 0:
                continue
            found = any(
                node.get("speaker") == speaker and text.strip() in node.get("text", "")
                for node in nodes.values()
            )
            assert found, f"Sampled script line not found in graph: {speaker}: {text}"

    elif check_type == "first_node_check":
        script_path = "/app/outpost_script.txt" if os.path.exists("/app/outpost_script.txt") else "outpost_script.txt"
        with open(script_path, "r", encoding="utf-8") as handle:
            first_header = next((line for line in handle if line.strip().startswith("[")), None)

        assert first_header, "Script has no section headers"
        match = re.match(r"^\[(.*?)\]", first_header.strip())
        assert match, "Could not parse first section header"
        assert match.group(1) == "Start", f"Expected first section to be Start, got {match.group(1)}"
        assert "Start" in nodes, "First node 'Start' missing from output graph"


@pytest.mark.parametrize("source,target", [
    ("Start", "GateChallenge"),
    ("GateChallenge", "NegotiationHub"),
    ("NegotiationHub", "CaravanPitch"),
    ("NegotiationHub", "ContractPitch"),
    ("ScoutChoice", "NegotiationHub"),
    ("MissingSealChoice", "BribeAttempt"),
    ("PassageChoice", "AidGranted"),
    ("ContractDecision", "ContractSealed"),
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
        assert "shape=diamond" in dot_content or 'shape="diamond"' in dot_content, (
            "Choice nodes should be visualized as diamonds"
        )
    elif viz_check == "content":
        assert "NegotiationHub" in dot_content, "Visualization missing NegotiationHub"
        assert "End" in dot_content, "Visualization missing End node"


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
