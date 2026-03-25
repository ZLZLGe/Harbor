#!/bin/bash

set -euo pipefail

python3 <<'PY'
import json
from collections import Counter

import yaml

INPUT_PATH = "/root/pod_egress_profiles.jsonl"
OUTPUT_PATH = "/root/pod_isolation_plan.yaml"
REASON_ORDER = ("port_scan", "dos_pattern", "beaconing")


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


records = []
with open(INPUT_PATH, "r", encoding="utf-8") as infile:
    for line in infile:
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))

pods = []
action_counts = Counter({"allow": 0, "observe": 0, "rate_limit": 0, "isolate": 0})

for record in records:
    flags = detect_flags(record)
    action = action_for(flags)
    pod_plan = {
        "namespace": record["namespace"],
        "pod_name": record["pod_name"],
        "action": action,
        "immediate_isolation": action == "isolate",
        "trigger_reasons": [name for name in REASON_ORDER if flags[name]],
    }
    pods.append(pod_plan)
    action_counts[action] += 1

plan = {
    "summary": {
        "total_pods": len(pods),
        "immediate_isolation_pods": sum(1 for pod in pods if pod["immediate_isolation"]),
        "action_counts": {
            "allow": action_counts["allow"],
            "observe": action_counts["observe"],
            "rate_limit": action_counts["rate_limit"],
            "isolate": action_counts["isolate"],
        },
    },
    "pods": pods,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as outfile:
    yaml.safe_dump(plan, outfile, sort_keys=False)
PY
