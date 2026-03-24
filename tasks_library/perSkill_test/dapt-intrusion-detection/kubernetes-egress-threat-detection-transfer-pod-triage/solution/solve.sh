#!/bin/bash

set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

INPUT_FILE = Path("/root/pod_egress_metrics.json")
OUTPUT_FILE = Path("/root/pod_egress_findings.json")
PRIORITY_ORDER = ["port_scan", "dos_pattern", "beaconing", "benign"]
PRIORITY_RANK = {label: index for index, label in enumerate(PRIORITY_ORDER)}


def has_port_scan(summary):
    return (
        summary["tcp_packet_count"] >= 50
        and summary["port_entropy"] > 6.0
        and summary["syn_only_ratio"] > 0.7
        and summary["unique_dst_ports"] > 100
    )


def has_dos_pattern(summary):
    avg = summary["packets_per_minute_avg"]
    if avg == 0:
        return False
    return (summary["packets_per_minute_max"] / avg) > 20


def has_beaconing(summary):
    return summary["iat_cv"] < 0.5


with INPUT_FILE.open() as f:
    payload = json.load(f)

queue = []
highest_priority_counts = {label: 0 for label in PRIORITY_ORDER}

for pod in payload["pods"]:
    summary = pod["egress_summary"]
    labels = []

    if has_port_scan(summary):
        labels.append("port_scan")
    if has_dos_pattern(summary):
        labels.append("dos_pattern")
    if has_beaconing(summary):
        labels.append("beaconing")
    if not labels:
        labels = ["benign"]

    highest_priority_reason = labels[0]
    highest_priority_counts[highest_priority_reason] += 1

    queue.append(
        {
            "namespace": pod["namespace"],
            "pod": pod["pod"],
            "owner": pod["owner"],
            "labels": labels,
            "highest_priority_reason": highest_priority_reason,
        }
    )

queue.sort(
    key=lambda item: (
        PRIORITY_RANK[item["highest_priority_reason"]],
        item["namespace"],
        item["pod"],
    )
)

summary = {
    "total_pods": len(queue),
    "malicious_pods": sum(1 for item in queue if item["highest_priority_reason"] != "benign"),
    "benign_pods": sum(1 for item in queue if item["highest_priority_reason"] == "benign"),
    "highest_priority_counts": highest_priority_counts,
}

output = {
    "cluster": payload["cluster"],
    "priority_order": PRIORITY_ORDER,
    "queue": queue,
    "summary": summary,
}

with OUTPUT_FILE.open("w") as f:
    json.dump(output, f, indent=2)
    f.write("\n")
PY
