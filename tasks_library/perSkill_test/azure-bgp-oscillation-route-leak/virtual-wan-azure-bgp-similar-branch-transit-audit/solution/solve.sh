#!/bin/bash
set -euo pipefail

cat > /tmp/solve_branch_transit_audit.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
DATA_DIR = APP_ROOT / "data"
OUTPUT_DIR = APP_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "branch_transit_audit.json"


FORBIDDEN_KEYWORDS = [
    "disable hub-to-hub",
    "disable hub peering",
    "disable peering",
    "remove branch connection",
    "remove connectivity",
    "shut down",
    "shutdown",
]

CYCLE_KEYWORDS = [
    "no longer prefers",
    "routing intent",
    "route preference hierarchy",
    "user defined route override",
]

LEAK_KEYWORDS = [
    "block provider-learned",
    "no-export community",
    "routing intent",
    "user defined route override",
    "as-path filtering",
    "reject core asn",
]


def load_json(name: str):
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def find_cycle(preferences: dict[str, dict[str, int]]) -> list[int]:
    pref_map = {
        int(asn): int(details["prefer_via"])
        for asn, details in preferences.items()
        if "prefer_via" in details
    }

    seen_global: set[int] = set()
    for start in pref_map:
        if start in seen_global:
            continue
        path: list[int] = []
        positions: dict[int, int] = {}
        current = start
        while current in pref_map:
            if current in positions:
                cycle = path[positions[current]:]
                return sorted(cycle)
            if current in seen_global:
                break
            positions[current] = len(path)
            path.append(current)
            seen_global.add(current)
            current = pref_map[current]
    return []


def is_valley_free_violation(event: dict[str, object]) -> bool:
    source_type = event["source_type"]
    destination_type = event["destination_type"]
    return (
        (source_type == "provider" and destination_type in {"peer", "provider"})
        or (source_type == "peer" and destination_type in {"peer", "provider"})
    )


def score_action(allowed: bool, breaks_cycle: bool, stops_leak: bool) -> int:
    if not allowed:
        return 0
    fixes = int(breaks_cycle) + int(stops_leak)
    if fixes == 2:
        return 100
    if fixes == 1:
        return 60
    return 20


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    preferences = load_json("preferences.json")
    route_events = load_json("route_events.json")
    candidate_fixes = load_json("candidate_fixes.json")

    hub_cycle = find_cycle(preferences)
    branch_route_leaks = []
    for event in route_events:
        if is_valley_free_violation(event):
            branch_route_leaks.append(
                {
                    "leaker_as": event["advertiser_asn"],
                    "source_as": event["source_asn"],
                    "destination_as": event["destination_asn"],
                    "source_type": event["source_type"],
                    "destination_type": event["destination_type"],
                    "branch_id": event["branch_id"],
                    "prefix": event["prefix"],
                }
            )

    policy_assessments = {}
    rejected_forbidden_actions = []

    for action in candidate_fixes:
        allowed = not contains_any(action, FORBIDDEN_KEYWORDS)
        breaks_cycle = allowed and contains_any(action, CYCLE_KEYWORDS)
        stops_leak = allowed and contains_any(action, LEAK_KEYWORDS)
        policy_assessments[action] = {
            "allowed": allowed,
            "breaks_cycle": breaks_cycle,
            "stops_leak": stops_leak,
            "score": score_action(allowed, breaks_cycle, stops_leak),
        }
        if not allowed:
            rejected_forbidden_actions.append(action)

    rejected_forbidden_actions.sort()

    output = {
        "hub_cycle_detected": bool(hub_cycle),
        "hub_cycle": hub_cycle,
        "affected_hubs": hub_cycle,
        "branch_route_leak_detected": bool(branch_route_leaks),
        "branch_route_leaks": branch_route_leaks,
        "policy_assessments": policy_assessments,
        "rejected_forbidden_actions": rejected_forbidden_actions,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
PY

python /tmp/solve_branch_transit_audit.py
