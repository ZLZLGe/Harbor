import glob
import json
import os
import re
import sys
from collections import Counter, deque

import pytest

for skill_path in [
    "/app/environment/skills/dialogue_graph/scripts",
    "/root/.codex/skills/dialogue_graph/scripts",
    "environment/skills/dialogue_graph/scripts",
]:
    if os.path.exists(skill_path):
        sys.path.insert(0, skill_path)
        break


def parse_playbook(text):
    sections = []
    current_id = None
    current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            if current_id is not None:
                sections.append((current_id, current_lines))
            current_id = line[1:-1].strip()
            current_lines = []
            continue
        if current_id is None:
            raise ValueError(f"Content found before header: {line}")
        current_lines.append(line)

    if current_id is not None:
        sections.append((current_id, current_lines))

    expected_nodes = {}
    expected_edges = []
    section_order = []

    for node_id, lines in sections:
        section_order.append(node_id)
        assert lines, f"Section {node_id} must not be empty"

        first_line = lines[0]
        if re.match(r"^\d+\.\s+", first_line):
            expected_nodes[node_id] = {"type": "choice", "speaker": "", "text": ""}
            for line in lines:
                edge_text, target = line.rsplit("->", 1)
                expected_edges.append((node_id, target.strip(), edge_text.strip()))
        else:
            text_part, target = first_line.rsplit("->", 1)
            speaker, text_value = text_part.split(":", 1)
            expected_nodes[node_id] = {
                "type": "line",
                "speaker": speaker.strip(),
                "text": text_value.strip(),
            }
            expected_edges.append((node_id, target.strip(), ""))

    return {
        "section_order": section_order,
        "nodes": expected_nodes,
        "edges": expected_edges,
    }


@pytest.fixture(scope="module")
def playbook_text():
    candidates = [
        "/app/drill_playbook.txt",
        "drill_playbook.txt",
        "environment/drill_playbook.txt",
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
    pytest.fail("drill_playbook.txt not found")


@pytest.fixture(scope="module")
def expected_model(playbook_text):
    return parse_playbook(playbook_text)


@pytest.fixture(scope="module")
def graph_data():
    candidates = [
        "/app/drill_playbook_graph.json",
        "drill_playbook_graph.json",
        "/root/drill_playbook_graph.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)

    for match in glob.glob("/app/**/drill_playbook_graph.json", recursive=True):
        with open(match, "r", encoding="utf-8") as handle:
            return json.load(handle)

    pytest.fail("drill_playbook_graph.json not found")


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
def dot_text():
    candidates = [
        "/app/drill_playbook_graph.dot",
        "drill_playbook_graph.dot",
        "/root/drill_playbook_graph.dot",
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
    pytest.fail("drill_playbook_graph.dot not found")


def test_output_matches_playbook_structure(graph_data, nodes, edges, expected_model):
    assert set(graph_data.keys()) == {"nodes", "edges"}, "Output JSON must contain only nodes and edges"
    assert set(nodes) == set(expected_model["nodes"]), "Node IDs must match the playbook headers exactly"
    assert len(nodes) == len(expected_model["nodes"]), "Unexpected node count"
    assert len(edges) == len(expected_model["edges"]), "Unexpected edge count"

    output_edges = {(edge["from"], edge["to"], edge["text"]) for edge in edges}
    assert output_edges == set(expected_model["edges"]), "Edges must match the transitions defined in the playbook"

    for node_id, expected in expected_model["nodes"].items():
        actual = nodes[node_id]
        assert actual["type"] == expected["type"], f"Node type mismatch for {node_id}"
        assert actual["speaker"] == expected["speaker"], f"Speaker mismatch for {node_id}"
        assert actual["text"] == expected["text"], f"Text mismatch for {node_id}"


def test_graph_reachability_and_hubs(nodes, edges, edge_map, expected_model):
    for edge in edges:
        assert edge["from"] in nodes, f"Missing edge source {edge['from']}"
        if edge["to"] != "End":
            assert edge["to"] in nodes, f"Missing edge target {edge['to']}"

    queue = deque([expected_model["section_order"][0]])
    reachable = set()
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        for target in edge_map.get(current, []):
            if target != "End":
                queue.append(target)

    assert reachable == set(nodes), "Every node must be reachable from the first section"

    expected_incoming = Counter(target for _, target, _ in expected_model["edges"] if target != "End")
    actual_incoming = Counter(edge["to"] for edge in edges if edge["to"] != "End")
    for hub in ["ReportReview", "SeverityTriage", "CleanupPlanning", "RecoveryChecklist"]:
        assert actual_incoming[hub] == expected_incoming[hub], f"Incoming edge count mismatch for {hub}"


def test_domain_specific_routes(edges, edge_map):
    output_edges = {(edge["from"], edge["to"], edge["text"]) for edge in edges}

    required_tagged_edges = {
        ("ReportIntake", "SmokeObservation", "1. [Observe: Smoke] Report light haze near the battery charging cages."),
        ("SeverityTriage", "SiteLeadEscalation", "3. [Escalate: Site Lead] Classify the event as a site-level emergency."),
        ("NotificationMatrix", "OpsBroadcast", "1. [Notify: Warehouse Ops] Send the restart estimate to floor leads."),
        ("RecoveryChoice", "DebriefMeeting", "3. [Wrap-Up] Hold the final debrief before restart."),
    }
    for edge in required_tagged_edges:
        assert edge in output_edges, f"Missing tagged route {edge}"

    assert set(edge_map["SeverityTriage"]) == {
        "LowResponse",
        "LimitedResponse",
        "SiteLeadEscalation",
        "FalseAlarmReview",
    }, "SeverityTriage must preserve the four response classes"

    assert set(edge_map["NotificationMatrix"]) == {
        "OpsBroadcast",
        "HRTrainingNotice",
        "LeadershipSummary",
        "SecurityNotice",
        "RecoveryChecklist",
    }, "NotificationMatrix must preserve all notification and recovery routes"

    assert set(edge_map["RestartDecision"]) == {
        "OperationsResume",
        "PartialResume",
        "InvestigationReview",
    }, "RestartDecision must preserve all restart outcomes"


def test_terminal_nodes_and_dot_output(edges, dot_text):
    end_sources = {edge["from"] for edge in edges if edge["to"] == "End"}
    assert end_sources == {
        "FalseAlarmClosed",
        "InvestigationClosed",
        "DrillComplete",
        "OperationsResume",
        "PartialResume",
    }, "Unexpected terminal nodes"

    assert "digraph" in dot_text, "DOT output must declare a digraph"
    assert "shape=diamond" in dot_text or 'shape=\"diamond\"' in dot_text, "Choice nodes should use diamond shapes"
    assert "ReportReview" in dot_text, "DOT output must include ReportReview"
    assert "SeverityTriage" in dot_text, "DOT output must include SeverityTriage"
    assert "CleanupPlanning" in dot_text, "DOT output must include CleanupPlanning"
    assert "RecoveryChecklist" in dot_text, "DOT output must include RecoveryChecklist"
    assert "END" in dot_text, "DOT output must include the terminal End node"


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
