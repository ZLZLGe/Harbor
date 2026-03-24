#!/bin/bash
set -euo pipefail

cat > /tmp/solve_failover_leak_review.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
DATA_DIR = APP_ROOT / "data"
OUTPUT_DIR = APP_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "failover_leak_review.json"


FORBIDDEN_KEYWORDS = [
    "disable the expressroute and vpn gateway peering",
    "shut down",
    "custom route map directly to the azure vpn gateway",
    "custom route map directly to the azure expressroute gateway",
]

CYCLE_KEYWORDS = [
    "no longer prefers",
    "preference hierarchy",
    "user defined route override",
    "clear the failover preference override",
]

LEAK_KEYWORDS = [
    "block azure-edge-learned",
    "no-export community",
    "user defined route override",
    "as-path filtering",
    "export filter",
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
                return sorted(path[positions[current]:])
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
    candidate_remediations = load_json("candidate_remediations.json")

    failover_cycle = find_cycle(preferences)
    upstream_route_leaks = []
    for event in route_events:
        if is_valley_free_violation(event):
            upstream_route_leaks.append(
                {
                    "leaker_as": event["advertiser_asn"],
                    "source_as": event["source_asn"],
                    "destination_as": event["destination_asn"],
                    "source_type": event["source_type"],
                    "destination_type": event["destination_type"],
                    "prefix": event["prefix"],
                    "origin_asn": event["origin_asn"],
                    "path_label": event["path_label"],
                }
            )

    remediation_assessments = {}
    forbidden_actions = []

    for action in candidate_remediations:
        allowed = not contains_any(action, FORBIDDEN_KEYWORDS)
        breaks_cycle = allowed and contains_any(action, CYCLE_KEYWORDS)
        stops_leak = allowed and contains_any(action, LEAK_KEYWORDS)
        remediation_assessments[action] = {
            "allowed": allowed,
            "breaks_cycle": breaks_cycle,
            "stops_leak": stops_leak,
            "score": score_action(allowed, breaks_cycle, stops_leak),
        }
        if not allowed:
            forbidden_actions.append(action)

    forbidden_actions.sort()

    output = {
        "failover_cycle_detected": bool(failover_cycle),
        "failover_cycle": failover_cycle,
        "affected_gateways": failover_cycle,
        "upstream_route_leak_detected": bool(upstream_route_leaks),
        "upstream_route_leaks": upstream_route_leaks,
        "remediation_assessments": remediation_assessments,
        "forbidden_actions": forbidden_actions,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
PY

python /tmp/solve_failover_leak_review.py
