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
        "/app/incident_triage_map.json",
        "incident_triage_map.json",
        "/root/incident_triage_map.json",
    ]
    for path in direct_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    for pattern in [
        "/app/**/incident_triage_map.json",
        "/root/**/incident_triage_map.json",
        "./**/incident_triage_map.json",
    ]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            with open(matches[0], "r", encoding="utf-8") as f:
                return json.load(f)

    pytest.fail("incident_triage_map.json not found in expected locations")


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
        "/app/incident_triage_map.dot",
        "incident_triage_map.dot",
        "/root/incident_triage_map.dot",
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    pytest.fail("incident_triage_map.dot not found in expected locations")


@pytest.fixture(scope="module")
def handbook_content():
    for path in [
        "/app/incident_triage_handbook.md",
        "incident_triage_handbook.md",
        "environment/incident_triage_handbook.md",
        "/root/incident_triage_handbook.md",
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    pytest.fail("incident_triage_handbook.md not found in expected locations")


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
        assert len(nodes) >= 50, f"Expected at least 50 nodes, got {len(nodes)}"
        assert len(edges) >= 80, f"Expected at least 80 edges, got {len(edges)}"

    elif check == "choice_density":
        choice_nodes = [node for node in nodes.values() if node["type"] == "choice"]
        assert len(choice_nodes) >= 17, f"Expected at least 17 choice nodes, got {len(choice_nodes)}"


@pytest.mark.parametrize(
    "category,expected",
    [
        ("speaker", "Monitor"),
        ("speaker", "IncidentLead"),
        ("speaker", "ReleaseEngineer"),
        ("speaker", "SRE"),
        ("speaker", "Database"),
        ("speaker", "Comms"),
        ("speaker", "Observability"),
        ("speaker", "EdgeTeam"),
        ("node", "AlertIngress"),
        ("node", "SeverityGate"),
        ("node", "DependencyChoice"),
        ("node", "StabilizationReview"),
        ("node", "RecoveryChoice"),
        ("node", "ManualMitigationHandoff"),
    ],
)
def test_incident_semantics(nodes, category, expected):
    if category == "speaker":
        speakers = {node["speaker"] for node in nodes.values() if node["speaker"]}
        assert expected in speakers, f"Missing required speaker {expected}"
    else:
        assert expected in nodes, f"Missing required node {expected}"


@pytest.mark.parametrize(
    "kind,identifier,fragment",
    [
        ("node_text", "SevOneBridge", "assign an incident scribe"),
        ("node_text", "FailoverStep", "Promote the healthy replica"),
        ("node_text", "ManualMitigationHandoff", "timeline, open hypotheses, and customer impact notes"),
        ("edge_text", "SeverityGate", "1. [SEV-1] Error rate is above 20% or checkout is fully down."),
        ("edge_text", "RollbackChoice", "1. [Feature Flag] Disable the new feature flag before touching the build."),
        ("edge_text", "DependencyChoice", "1. [Vendor Escalation] A third-party API latency spike dominates the traces."),
        ("edge_text", "CapacityChoice", "2. [Queue Drain] Pause noncritical jobs and drain the backlog first."),
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
    [
        "edge_targets",
        "reachability",
        "sev_one_routes",
        "stabilization_hub",
        "terminal_sources",
        "recheck_loops",
    ],
)
def test_incident_logic(nodes, edges, edge_map, check):
    if check == "edge_targets":
        for edge in edges:
            assert edge["from"] in nodes, f"Missing edge source {edge['from']}"
            if edge["to"] != "End":
                assert edge["to"] in nodes, f"Missing edge target {edge['to']}"

    elif check == "reachability":
        reachable = set()
        queue = deque(["AlertIngress"])
        while queue:
            current = queue.popleft()
            if current in reachable or current == "End":
                continue
            reachable.add(current)
            for target in edge_map.get(current, []):
                queue.append(target)

        unreachable = set(nodes) - reachable
        assert not unreachable, f"Found unreachable nodes: {sorted(unreachable)[:5]}"

    elif check == "sev_one_routes":
        incoming = Counter(edge["to"] for edge in edges)
        assert incoming["SevOneBridge"] >= 5, f"Expected at least 5 routes into SevOneBridge, got {incoming['SevOneBridge']}"
        assert len(edge_map.get("SeverityGate", [])) == 3, "SeverityGate should expose three top-level triage branches"

    elif check == "stabilization_hub":
        incoming = Counter(edge["to"] for edge in edges)
        assert incoming["StabilizationReview"] >= 10, f"Expected at least 10 routes into StabilizationReview, got {incoming['StabilizationReview']}"
        assert "RecoverySummary" in edge_map.get("StabilizationChoice", []), "Stable incidents should route into RecoverySummary"

    elif check == "terminal_sources":
        terminal_sources = {edge["from"] for edge in edges if edge["to"] == "End"}
        assert terminal_sources == {
            "FalseAlarmClosed",
            "RollbackComplete",
            "CapacityRecovered",
            "DependencyMitigated",
            "FeatureFlagRecovered",
            "ManualMitigationHandoff",
        }, f"Unexpected terminal sources: {sorted(terminal_sources)}"

    elif check == "recheck_loops":
        assert "ServiceCheckChoice" in edge_map.get("BridgeChoice", []), "BridgeChoice should loop back to ServiceCheckChoice"
        assert "DependencyCheck" in edge_map.get("BridgeChoice", []), "BridgeChoice should loop back to DependencyCheck"
        assert "SevOneBridge" in edge_map.get("StabilizationChoice", []), "StabilizationChoice should re-escalate to SevOneBridge when impact widens"


@pytest.mark.parametrize("check", ["choice_shapes", "tagged_edges", "review_nodes", "end_marker"])
def test_visualization(dot_content, check):
    if check == "choice_shapes":
        assert "shape=\"diamond\"" in dot_content or "shape=diamond" in dot_content, "Choice nodes should be diamonds"

    elif check == "tagged_edges":
        assert "darkblue" in dot_content, "Tagged incident branches should use dark blue styling"
        assert "style=\"bold\"" in dot_content or "style=bold" in dot_content, "Tagged incident branches should be bold"

    elif check == "review_nodes":
        assert "StabilizationReview" in dot_content, "DOT output should include StabilizationReview"
        assert "ManualMitigationHandoff" in dot_content, "DOT output should include ManualMitigationHandoff"

    elif check == "end_marker":
        assert "END" in dot_content, "DOT output should include the terminal End node"


@pytest.mark.parametrize("check", ["first_header", "sample_headers", "sample_dialogue", "sample_choices"])
def test_input_alignment(nodes, edges, handbook_content, check):
    headers = re.findall(r"^\[(.*?)\]$", handbook_content, re.MULTILINE)
    dialogue_lines = re.findall(r"^([^:\n]+):\s+(.+?)\s+->\s+([A-Za-z0-9_]+)$", handbook_content, re.MULTILINE)
    choice_lines = re.findall(r"^(\d+\.\s+.+?)\s+->\s+([A-Za-z0-9_]+)$", handbook_content, re.MULTILINE)

    if check == "first_header":
        assert headers[0] == "AlertIngress", f"Unexpected first header: {headers[0]}"
        assert "AlertIngress" in nodes, "First handbook node missing from output"

    elif check == "sample_headers":
        for header in headers[::4]:
            assert header in nodes, f"Header node {header} from handbook missing in graph"

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
