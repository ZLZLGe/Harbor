import json
from pathlib import Path


RESULTS_FILE = Path("/root/pod_egress_findings.json")

EXPECTED_OUTPUT = {
    "cluster": "harbor-west-2",
    "priority_order": ["port_scan", "dos_pattern", "beaconing", "benign"],
    "queue": [
        {
            "namespace": "b2b",
            "pod": "partner-sync-68c7dd4f54-txqnr",
            "owner": "deployment/partner-sync",
            "labels": ["port_scan"],
            "highest_priority_reason": "port_scan",
        },
        {
            "namespace": "edge",
            "pod": "asset-indexer-7c89d9d7b9-2kgr2",
            "owner": "deployment/asset-indexer",
            "labels": ["port_scan", "dos_pattern", "beaconing"],
            "highest_priority_reason": "port_scan",
        },
        {
            "namespace": "telemetry",
            "pod": "node-export-5dbfdcb85d-l2vqb",
            "owner": "daemonset/node-export",
            "labels": ["dos_pattern", "beaconing"],
            "highest_priority_reason": "dos_pattern",
        },
        {
            "namespace": "jobs",
            "pod": "cron-notifier-28542000-zx8k2",
            "owner": "job/cron-notifier",
            "labels": ["beaconing"],
            "highest_priority_reason": "beaconing",
        },
        {
            "namespace": "storage",
            "pod": "object-mirror-6b7d9fdbf8-jr2pl",
            "owner": "statefulset/object-mirror",
            "labels": ["beaconing"],
            "highest_priority_reason": "beaconing",
        },
        {
            "namespace": "checkout",
            "pod": "frontend-api-7f9cf6d68c-hk2rw",
            "owner": "deployment/frontend-api",
            "labels": ["benign"],
            "highest_priority_reason": "benign",
        },
        {
            "namespace": "compliance",
            "pod": "report-exporter-6fd89c4c77-rt9nq",
            "owner": "deployment/report-exporter",
            "labels": ["benign"],
            "highest_priority_reason": "benign",
        },
        {
            "namespace": "kube-system",
            "pod": "dns-cache-5f8d7c9b6-mrx1c",
            "owner": "deployment/dns-cache",
            "labels": ["benign"],
            "highest_priority_reason": "benign",
        },
    ],
    "summary": {
        "total_pods": 8,
        "malicious_pods": 5,
        "benign_pods": 3,
        "highest_priority_counts": {
            "port_scan": 2,
            "dos_pattern": 1,
            "beaconing": 2,
            "benign": 3,
        },
    },
}


def load_results():
    assert RESULTS_FILE.exists(), "Results file not found"
    with RESULTS_FILE.open() as f:
        return json.load(f)


def test_output_matches_expected_structure():
    results = load_results()
    assert results == EXPECTED_OUTPUT


def test_queue_is_sorted_by_priority_then_name():
    results = load_results()
    queue = results["queue"]
    expected_pairs = [
        ("port_scan", "b2b", "partner-sync-68c7dd4f54-txqnr"),
        ("port_scan", "edge", "asset-indexer-7c89d9d7b9-2kgr2"),
        ("dos_pattern", "telemetry", "node-export-5dbfdcb85d-l2vqb"),
        ("beaconing", "jobs", "cron-notifier-28542000-zx8k2"),
        ("beaconing", "storage", "object-mirror-6b7d9fdbf8-jr2pl"),
        ("benign", "checkout", "frontend-api-7f9cf6d68c-hk2rw"),
        ("benign", "compliance", "report-exporter-6fd89c4c77-rt9nq"),
        ("benign", "kube-system", "dns-cache-5f8d7c9b6-mrx1c"),
    ]
    actual_pairs = [
        (item["highest_priority_reason"], item["namespace"], item["pod"]) for item in queue
    ]
    assert actual_pairs == expected_pairs


def test_labels_are_priority_ordered():
    results = load_results()
    by_pod = {(item["namespace"], item["pod"]): item for item in results["queue"]}

    assert by_pod[("edge", "asset-indexer-7c89d9d7b9-2kgr2")]["labels"] == [
        "port_scan",
        "dos_pattern",
        "beaconing",
    ]
    assert by_pod[("telemetry", "node-export-5dbfdcb85d-l2vqb")]["labels"] == [
        "dos_pattern",
        "beaconing",
    ]
    assert by_pod[("kube-system", "dns-cache-5f8d7c9b6-mrx1c")]["labels"] == ["benign"]
