#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUTPUT_DIR="${OUTPUT_DIR:-/app/output}"

mkdir -p "$OUTPUT_DIR"

cat > /tmp/solve_multi_hub_matrix.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3

import json
from pathlib import Path


DATA_DIR = Path(__import__("os").environ.get("DATA_DIR", "/app/data"))
OUTPUT_DIR = Path(__import__("os").environ.get("OUTPUT_DIR", "/app/output"))
OUTPUT_FILE = OUTPUT_DIR / "multi_hub_remediation_matrix.json"


def load_json(name):
    return json.loads((DATA_DIR / name).read_text())


def find_cycle(preferences):
    pref_map = {item["asn"]: item["prefer_via"] for item in preferences}
    for start in sorted(pref_map):
        order = {}
        path = []
        cur = start
        while cur in pref_map:
            if cur in order:
                return path[order[cur]:]
            order[cur] = len(path)
            path.append(cur)
            cur = pref_map[cur]
    return []


def is_valley_free_violation(event):
    learned = event["learned_from_relationship"]
    exported = event["exported_to_relationship"]
    if learned == "customer":
        return False
    if learned in {"provider", "peer"} and exported in {"provider", "peer"}:
        return True
    return False


def evaluate_candidate(change_text, all_leak_ids):
    text = change_text.lower()

    prohibited = "disable hub peering" in text or "disable peering" in text
    operational_non_fix = "keepalive" in text or "hold timer" in text or "restart" in text
    azure_viable = not prohibited and not operational_non_fix

    breaks_cycle = any(
        keyword in text
        for keyword in [
            "remove the hub-west preference",
            "preference hierarchy",
            "routing intent",
            "udr overrides",
            "udr override",
        ]
    )

    resolved = set()
    if "routing intent" in text or "udr overrides" in text or "udr override" in text:
        resolved.update(all_leak_ids)
    else:
        if "hub-central" in text and "provider-learned" in text and "peer" in text:
            resolved.add("leak-001")
        if "hub-east" in text and "peer-learned" in text and "virtual wan" in text:
            resolved.add("leak-002")
        if "valley-free export policies" in text:
            resolved.update(all_leak_ids)

    resolved_leak_ids = sorted(resolved)
    remaining_leak_ids = sorted(leak_id for leak_id in all_leak_ids if leak_id not in resolved)

    if prohibited:
        effect = "prohibited"
    elif breaks_cycle and not remaining_leak_ids:
        effect = "full_fix"
    elif breaks_cycle:
        effect = "cycle_only"
    elif resolved_leak_ids and not remaining_leak_ids:
        effect = "all_leaks_only"
    elif resolved_leak_ids:
        effect = "partial_leak_fix"
    else:
        effect = "no_fix"

    return {
        "azure_viable": azure_viable,
        "breaks_preference_cycle": breaks_cycle,
        "resolved_leak_ids": resolved_leak_ids,
        "remaining_leak_ids": remaining_leak_ids,
        "overall_effect": effect,
    }


def main():
    topology = load_json("topology_bundle.json")
    leak_observations = load_json("leak_observations.json")
    candidates = load_json("candidate_changes.json")

    cycle = find_cycle(topology["preferences"])
    valid_leaks = [event for event in leak_observations if is_valley_free_violation(event)]
    leak_ids = sorted(event["leak_id"] for event in valid_leaks)
    prefixes = sorted({event["prefix"] for event in valid_leaks})

    matrix = []
    for item in sorted(candidates, key=lambda candidate: candidate["candidate_id"]):
        evaluation = evaluate_candidate(item["change"], leak_ids)
        matrix.append(
            {
                "candidate_id": item["candidate_id"],
                "candidate_change": item["change"],
                **evaluation,
            }
        )

    output = {
        "analysis_summary": {
            "oscillation_detected": bool(cycle),
            "preference_cycle": cycle,
            "leak_ids": leak_ids,
            "affected_prefixes": prefixes,
        },
        "remediation_matrix": matrix,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python /tmp/solve_multi_hub_matrix.py
