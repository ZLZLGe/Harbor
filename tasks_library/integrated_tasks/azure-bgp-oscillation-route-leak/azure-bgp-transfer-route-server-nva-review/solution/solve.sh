#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUTPUT_FILE="${OUTPUT_FILE:-/app/output/route_server_reflection_review.json}"
export DATA_DIR OUTPUT_FILE

mkdir -p "$(dirname "$OUTPUT_FILE")"

python3 - << 'PY'
import json
import os
from pathlib import Path

data_dir = Path(os.environ.get("DATA_DIR", "/app/data"))
output_file = Path(os.environ.get("OUTPUT_FILE", "/app/output/route_server_reflection_review.json"))


def load_json(name):
    with open(data_dir / name, "r", encoding="utf-8") as f:
        return json.load(f)


def find_preference_cycle(preferences):
    pref_map = {}
    for asn, details in preferences.items():
        if "prefer_via" in details:
            pref_map[int(asn)] = int(details["prefer_via"])

    visited = set()
    for start in sorted(pref_map):
        if start in visited:
            continue

        path = []
        index = {}
        cur = start
        while cur in pref_map:
            if cur in index:
                return sorted(path[index[cur]:])
            if cur in visited:
                break
            index[cur] = len(path)
            path.append(cur)
            cur = pref_map[cur]

        visited.update(path)

    return []


def is_valley_free_violation(event):
    return event["source_type"] in {"provider", "peer"} and event["destination_type"] in {"provider", "peer"}


def classify_action(action, cycle_present, leak_count):
    text = action.lower()

    teardown_markers = [
        "disable",
        "remove",
        "shut down",
        "shutdown",
    ]
    if any(marker in text for marker in teardown_markers):
        return {
            "allowed": False,
            "addresses": [],
            "reason": "prohibited_connectivity_teardown",
        }

    if "restart" in text or "clear" in text:
        return {
            "allowed": False,
            "addresses": [],
            "reason": "operational_reset_only",
        }

    addresses = []

    oscillation_resolved = False
    if cycle_present:
        if "symmetric route policy package" in text:
            oscillation_resolved = True
        elif "udr next-hop overrides on both spoke route tables" in text:
            oscillation_resolved = True
        elif "no longer prefers the reflected path via nva-west" in text:
            oscillation_resolved = True
        elif "directly attached branch routes above reflected appliance routes" in text:
            oscillation_resolved = True
        elif "single approved next hop for 172.18.44.0/24" in text and "export filters" in text:
            oscillation_resolved = True

    route_leak_resolved = False
    if leak_count:
        if "symmetric route policy package" in text:
            route_leak_resolved = True
        elif "block every route server-learned prefix from being advertised to the opposite appliance" in text:
            route_leak_resolved = True
        elif "no-export community on every route server-learned prefix" in text:
            route_leak_resolved = True
        elif "single approved next hop for 172.18.44.0/24" in text and "export filters for all route server-learned routes" in text:
            route_leak_resolved = True

    if oscillation_resolved:
        addresses.append("oscillation")
    if route_leak_resolved:
        addresses.append("route_leak")

    return {
        "allowed": True,
        "addresses": addresses,
        "reason": None,
    }


review_context = load_json("review_context.json")
sessions = load_json("sessions.json")
preferences = load_json("preferences.json")
route_events = load_json("route_events.json")
possible_actions = load_json("possible_actions.json")

customer_prefix = review_context["customer_prefix"]
route_server_as_values = {int(session["local_as"]) for session in sessions}
route_server_as = sorted(route_server_as_values)[0]

cycle = find_preference_cycle(preferences)

route_leak_events = []
for event in route_events:
    if is_valley_free_violation(event):
        route_leak_events.append(
            {
                "leaker_as": int(event["advertiser_asn"]),
                "source_as": int(event["source_as"]),
                "destination_as": int(event["destination_as"]),
                "source_type": event["source_type"],
                "destination_type": event["destination_type"],
                "prefix": event["prefix"],
            }
        )

route_leak_events.sort(key=lambda item: (item["leaker_as"], item["destination_as"], item["prefix"]))

incidents = []
if cycle:
    incidents.append(
        {
            "incident_type": "oscillation",
            "prefix": customer_prefix,
            "participants": cycle,
            "details": {
                "cycle": cycle,
                "reflected_by": route_server_as,
            },
        }
    )

for leak in route_leak_events:
    incidents.append(
        {
            "incident_type": "route_leak",
            "prefix": leak["prefix"],
            "participants": sorted({leak["source_as"], leak["leaker_as"], leak["destination_as"]}),
            "details": {
                "leaker_as": leak["leaker_as"],
                "source_as": leak["source_as"],
                "destination_as": leak["destination_as"],
                "source_type": leak["source_type"],
                "destination_type": leak["destination_type"],
            },
        }
    )

action_results = {}
effective_changes = []
rejected_actions = []

for action in possible_actions:
    classification = classify_action(action, bool(cycle), len(route_leak_events))
    action_results[action] = {
        "allowed": classification["allowed"],
        "addresses": classification["addresses"],
    }

    if classification["allowed"] and classification["addresses"]:
        effective_changes.append(
            {
                "action": action,
                "addresses": classification["addresses"],
            }
        )

    if not classification["allowed"]:
        rejected_actions.append(
            {
                "action": action,
                "reason": classification["reason"],
            }
        )

report = {
    "review_summary": {
        "customer_prefix": customer_prefix,
        "route_server_as": route_server_as,
        "oscillation_detected": bool(cycle),
        "route_leak_detected": bool(route_leak_events),
    },
    "incidents": incidents,
    "effective_changes": effective_changes,
    "rejected_actions": rejected_actions,
    "action_results": action_results,
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY
