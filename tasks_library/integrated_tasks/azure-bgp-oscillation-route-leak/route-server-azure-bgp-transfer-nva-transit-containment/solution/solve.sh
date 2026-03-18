#!/bin/bash
set -euo pipefail

cat > /tmp/solve_nva_transit_containment.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
DATA_DIR = APP_ROOT / "data"
OUTPUT_DIR = APP_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "nva_transit_containment.json"


FORBIDDEN_KEYWORDS = [
    "disable the bgp peering",
    "disable azure route server",
    "disable route server",
    "remove nva transit",
    "remove connectivity",
    "shut down",
    "shutdown",
]

CYCLE_KEYWORDS = [
    "no longer prefers",
    "route preference hierarchy",
    "user defined route",
    "peer preference override",
    "inbound prefix list",
]

LEAK_KEYWORDS = [
    "block azure route server-learned",
    "export filter",
    "no-export community",
    "user defined route",
    "as-path filtering",
    "reject asn 65200",
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
    candidate_mitigations = load_json("candidate_mitigations.json")

    nva_cycle = find_cycle(preferences)
    provider_route_leaks = []
    for event in route_events:
        if is_valley_free_violation(event):
            provider_route_leaks.append(
                {
                    "leaker_as": event["advertiser_asn"],
                    "source_as": event["source_asn"],
                    "destination_as": event["destination_asn"],
                    "source_type": event["source_type"],
                    "destination_type": event["destination_type"],
                    "prefix": event["prefix"],
                    "origin_asn": event["origin_asn"],
                    "route_server": event["route_server"],
                }
            )

    mitigation_assessments = {}
    forbidden_actions = []

    for action in candidate_mitigations:
        allowed = not contains_any(action, FORBIDDEN_KEYWORDS)
        breaks_cycle = allowed and contains_any(action, CYCLE_KEYWORDS)
        stops_leak = allowed and contains_any(action, LEAK_KEYWORDS)
        mitigation_assessments[action] = {
            "allowed": allowed,
            "breaks_cycle": breaks_cycle,
            "stops_leak": stops_leak,
            "score": score_action(allowed, breaks_cycle, stops_leak),
        }
        if not allowed:
            forbidden_actions.append(action)

    forbidden_actions.sort()

    output = {
        "nva_cycle_detected": bool(nva_cycle),
        "nva_cycle": nva_cycle,
        "affected_nvas": nva_cycle,
        "provider_route_leak_detected": bool(provider_route_leaks),
        "provider_route_leaks": provider_route_leaks,
        "mitigation_assessments": mitigation_assessments,
        "forbidden_actions": forbidden_actions,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
PY

python /tmp/solve_nva_transit_containment.py
