import glob
import json
import os
import re
import sys
from collections import Counter, deque

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
def graph_data():
    direct_paths = [
        "/app/warranty_returns_flow.json",
        "warranty_returns_flow.json",
        "/root/warranty_returns_flow.json",
    ]
    for path in direct_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    for pattern in [
        "/app/**/warranty_returns_flow.json",
        "/root/**/warranty_returns_flow.json",
        "./**/warranty_returns_flow.json",
    ]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            with open(matches[0], "r", encoding="utf-8") as f:
                return json.load(f)

    pytest.fail("warranty_returns_flow.json not found in expected locations")


@pytest.fixture(scope="module")
def nodes(graph_data):
    return {node["id"]: node for node in graph_data["nodes"]}


@pytest.fixture(scope="module")
def edges(graph_data):
    return graph_data["edges"]


@pytest.fixture(scope="module")
def edge_map(edges):
    mapping = {}
    for edge in edges:
        mapping.setdefault(edge["from"], []).append(edge["to"])
    return mapping


@pytest.fixture(scope="module")
def dot_content():
    for path in [
        "/app/warranty_returns_flow.dot",
        "warranty_returns_flow.dot",
        "/root/warranty_returns_flow.dot",
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    pytest.fail("warranty_returns_flow.dot not found in expected locations")


@pytest.fixture(scope="module")
def script_content():
    for path in [
        "/app/return_playbook.txt",
        "return_playbook.txt",
        "environment/return_playbook.txt",
        "/root/return_playbook.txt",
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    pytest.fail("return_playbook.txt not found in expected locations")


@pytest.mark.parametrize("check", ["files", "schema", "size", "choice_density"])
def test_system_basics(graph_data, nodes, edges, dot_content, check):
    if check == "files":
        assert isinstance(graph_data.get("nodes"), list), "nodes must be a list"
        assert isinstance(graph_data.get("edges"), list), "edges must be a list"
        assert "digraph" in dot_content, "DOT output must contain a digraph"

    elif check == "schema":
        for node in graph_data["nodes"]:
            assert isinstance(node.get("id"), str) and node["id"], f"Invalid node id: {node}"
            assert isinstance(node.get("text"), str), f"Node {node.get('id')} missing text"
            assert isinstance(node.get("speaker"), str), f"Node {node.get('id')} missing speaker"
            assert node.get("type") in {"line", "choice"}, f"Node {node.get('id')} has invalid type"
        for edge in graph_data["edges"]:
            assert isinstance(edge.get("from"), str) and edge["from"], f"Invalid edge source: {edge}"
            assert isinstance(edge.get("to"), str) and edge["to"], f"Invalid edge target: {edge}"
            assert isinstance(edge.get("text"), str), f"Edge missing text field: {edge}"

    elif check == "size":
        assert len(nodes) >= 30, f"Expected at least 30 nodes, got {len(nodes)}"
        assert len(edges) >= 40, f"Expected at least 40 edges, got {len(edges)}"

    elif check == "choice_density":
        choice_nodes = [node for node in nodes.values() if node["type"] == "choice"]
        assert len(choice_nodes) >= 10, f"Expected at least 10 choice nodes, got {len(choice_nodes)}"


@pytest.mark.parametrize(
    "category,expected",
    [
        ("speaker", "Assistant"),
        ("speaker", "PolicyBot"),
        ("speaker", "WarehouseAgent"),
        ("speaker", "Routing"),
        ("speaker", "ReturnsLead"),
        ("node", "Start"),
        ("node", "IntentMenu"),
        ("node", "DamageEvidenceChoice"),
        ("node", "ExchangeCheckChoice"),
        ("node", "HumanQueue"),
        ("node", "HumanHandoffConfirmed"),
    ],
)
def test_support_semantics(nodes, category, expected):
    if category == "speaker":
        speakers = {node["speaker"] for node in nodes.values() if node["speaker"]}
        assert expected in speakers, f"Missing required speaker {expected}"
    else:
        assert expected in nodes, f"Missing required node {expected}"


@pytest.mark.parametrize(
    "kind,identifier,fragment",
    [
        ("node_text", "SafetyEscalation", "bypass automation and go straight to a human safety specialist"),
        ("node_text", "RefundIssued", "carrier scans the return label"),
        ("node_text", "ExchangeCreated", "replacement confirmation and return instructions"),
        ("edge_text", "LookupChoice", "1. [Within 30 Days] Order is confirmed and the package is still sealed."),
        ("edge_text", "DamageEvidenceChoice", "1. [Photo Attached] I have box and product photos ready."),
        ("edge_text", "WarrantyTroubleshootChoice", "1. [Reset Completed] The device works after troubleshooting."),
    ],
)
def test_content_preservation(nodes, edges, kind, identifier, fragment):
    if kind == "node_text":
        assert identifier in nodes, f"Node {identifier} is missing"
        assert fragment in nodes[identifier]["text"], f"Node {identifier} text mismatch"
    else:
        matching = [edge for edge in edges if edge["from"] == identifier and edge["text"] == fragment]
        assert matching, f"Missing preserved option text on edge from {identifier}"


@pytest.mark.parametrize(
    "check",
    ["edge_targets", "reachability", "human_handoff_routes", "terminal_sources", "refund_loopback"],
)
def test_flow_logic(nodes, edges, edge_map, check):
    if check == "edge_targets":
        for edge in edges:
            assert edge["from"] in nodes, f"Missing edge source {edge['from']}"
            if edge["to"] != "End":
                assert edge["to"] in nodes, f"Missing edge target {edge['to']}"

    elif check == "reachability":
        reachable = set()
        queue = deque(["Start"])
        while queue:
            current = queue.popleft()
            if current in reachable or current == "End":
                continue
            reachable.add(current)
            for target in edge_map.get(current, []):
                queue.append(target)

        unreachable = set(nodes) - reachable
        assert not unreachable, f"Found unreachable nodes: {sorted(unreachable)[:5]}"

    elif check == "human_handoff_routes":
        incoming = Counter(edge["to"] for edge in edges)
        assert incoming["HumanQueue"] >= 9, f"Expected at least 9 routes into HumanQueue, got {incoming['HumanQueue']}"

    elif check == "terminal_sources":
        terminal_sources = {edge["from"] for edge in edges if edge["to"] == "End"}
        assert terminal_sources == {
            "HumanHandoffConfirmed",
            "RefundIssued",
            "StoreCreditOffered",
            "ExchangeCreated",
            "RequestDenied",
            "RequestClosed",
        }, f"Unexpected terminal sources: {sorted(terminal_sources)}"

    elif check == "refund_loopback":
        refund_targets = {edge["to"] for edge in edges if edge["from"] == "ExchangeCheckChoice"}
        assert "OrderLookup" in refund_targets, "ExchangeCheckChoice should be able to loop back into the refund lookup path"


@pytest.mark.parametrize("check", ["choice_shapes", "tagged_edges", "handoff_node", "end_marker"])
def test_visualization(dot_content, check):
    if check == "choice_shapes":
        assert "shape=diamond" in dot_content or 'shape="diamond"' in dot_content, "Choice nodes should be diamonds"

    elif check == "tagged_edges":
        assert "darkblue" in dot_content, "Tagged policy choices should use dark blue styling"
        assert "style=bold" in dot_content or 'style="bold"' in dot_content, "Tagged policy choices should be bold"

    elif check == "handoff_node":
        assert "HumanQueue" in dot_content, "DOT output should include HumanQueue"
        assert "HumanHandoffConfirmed" in dot_content, "DOT output should include HumanHandoffConfirmed"

    elif check == "end_marker":
        assert "END" in dot_content, "DOT output should include the terminal End node"


@pytest.mark.parametrize("check", ["first_header", "sample_headers", "sample_dialogue", "sample_choices"])
def test_input_alignment(nodes, edges, script_content, check):
    headers = re.findall(r"^\[(.*?)\]$", script_content, re.MULTILINE)
    dialogue_lines = re.findall(r"^([^:\n]+):\s+(.+?)\s+->\s+([A-Za-z0-9_]+)$", script_content, re.MULTILINE)
    choice_lines = re.findall(r"^(\d+\.\s+.+?)\s+->\s+([A-Za-z0-9_]+)$", script_content, re.MULTILINE)

    if check == "first_header":
        assert headers[0] == "Start", f"Unexpected first header: {headers[0]}"
        assert "Start" in nodes, "First script node missing from output"

    elif check == "sample_headers":
        for header in headers[::4]:
            assert header in nodes, f"Header node {header} from script missing in graph"

    elif check == "sample_dialogue":
        for speaker, text, _target in dialogue_lines[::4]:
            found = any(node["speaker"] == speaker and text in node["text"] for node in nodes.values())
            assert found, f"Dialogue line not found in graph: {speaker}: {text}"

    elif check == "sample_choices":
        for option_text, target in choice_lines[::3]:
            found = any(edge["text"] == option_text and edge["to"] == target for edge in edges)
            assert found, f"Choice line not preserved in graph: {option_text} -> {target}"


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
