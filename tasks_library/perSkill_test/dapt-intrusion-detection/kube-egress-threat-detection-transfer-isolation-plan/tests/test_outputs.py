import json
from pathlib import Path

import yaml


INPUT_FILE = Path("/root/pod_egress_profiles.jsonl")
OUTPUT_FILE = Path("/root/pod_isolation_plan.yaml")
REASON_ORDER = ("port_scan", "dos_pattern", "beaconing")
ALLOWED_ACTIONS = {"allow", "observe", "rate_limit", "isolate"}


def load_records():
    records = []
    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def load_plan():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as infile:
        return yaml.safe_load(infile)


def detect_flags(record):
    has_port_scan = (
        record["port_entropy"] > 6.0
        and record["syn_only_ratio"] > 0.7
        and record["unique_destination_ports"] > 100
    )

    avg = record["packets_per_minute_avg"]
    has_dos_pattern = False if avg == 0 else (record["packets_per_minute_max"] / avg) > 20
    has_beaconing = record["iat_cv"] < 0.5
    return {
        "port_scan": has_port_scan,
        "dos_pattern": has_dos_pattern,
        "beaconing": has_beaconing,
    }


def action_for(flags):
    if flags["port_scan"] or (flags["dos_pattern"] and flags["beaconing"]):
        return "isolate"
    if flags["dos_pattern"]:
        return "rate_limit"
    if flags["beaconing"]:
        return "observe"
    return "allow"


def expected_pods():
    expected = []
    for record in load_records():
        flags = detect_flags(record)
        expected.append(
            {
                "namespace": record["namespace"],
                "pod_name": record["pod_name"],
                "action": action_for(flags),
                "immediate_isolation": action_for(flags) == "isolate",
                "trigger_reasons": [name for name in REASON_ORDER if flags[name]],
            }
        )
    return expected


def expected_summary(pods):
    counts = {action: 0 for action in ALLOWED_ACTIONS}
    for pod in pods:
        counts[pod["action"]] += 1
    return {
        "total_pods": len(pods),
        "immediate_isolation_pods": sum(1 for pod in pods if pod["immediate_isolation"]),
        "action_counts": counts,
    }


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), "Missing /root/pod_isolation_plan.yaml"


def test_plan_shape():
    plan = load_plan()
    assert isinstance(plan, dict), "Output must be a YAML mapping"
    assert set(plan.keys()) == {"summary", "pods"}, "Top-level keys must be summary and pods"
    assert isinstance(plan["summary"], dict), "summary must be a YAML mapping"
    assert isinstance(plan["pods"], list), "pods must be a YAML list"


def test_pod_entries_match_expected_order_and_values():
    plan = load_plan()
    pods = plan["pods"]
    expected = expected_pods()

    assert len(pods) == len(expected), "Output must contain one plan entry per input Pod"

    for actual, exp in zip(pods, expected):
        assert isinstance(actual, dict), "Each pod plan entry must be a YAML mapping"
        assert set(actual.keys()) == {
            "namespace",
            "pod_name",
            "action",
            "immediate_isolation",
            "trigger_reasons",
        }, "Each pod entry must contain exactly the required keys"
        assert actual["namespace"] == exp["namespace"]
        assert actual["pod_name"] == exp["pod_name"]
        assert actual["action"] in ALLOWED_ACTIONS
        assert isinstance(actual["immediate_isolation"], bool), (
            "immediate_isolation must be a YAML boolean"
        )
        assert isinstance(actual["trigger_reasons"], list), "trigger_reasons must be a YAML list"

        assert actual["action"] == exp["action"]
        assert actual["immediate_isolation"] == exp["immediate_isolation"]
        assert actual["trigger_reasons"] == exp["trigger_reasons"]


def test_summary_matches_pod_entries():
    plan = load_plan()
    pods = plan["pods"]
    summary = plan["summary"]
    expected = expected_summary(pods)

    assert set(summary.keys()) == {
        "total_pods",
        "immediate_isolation_pods",
        "action_counts",
    }, "summary must contain total_pods, immediate_isolation_pods, and action_counts"
    assert summary["total_pods"] == expected["total_pods"]
    assert summary["immediate_isolation_pods"] == expected["immediate_isolation_pods"]

    action_counts = summary["action_counts"]
    assert isinstance(action_counts, dict), "action_counts must be a YAML mapping"
    assert set(action_counts.keys()) == ALLOWED_ACTIONS
    for action in ALLOWED_ACTIONS:
        assert isinstance(action_counts[action], int), "action_counts values must be integers"
        assert action_counts[action] == expected["action_counts"][action]


def test_action_and_isolation_consistency():
    plan = load_plan()

    for pod in plan["pods"]:
        if pod["action"] == "isolate":
            assert pod["immediate_isolation"] is True
        else:
            assert pod["immediate_isolation"] is False
