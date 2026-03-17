#!/usr/bin/env python3
"""Generate the branch transit audit dataset."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
ENV_DATA_DIR = APP_ROOT / "environment" / "data"
DATA_DIR = APP_ROOT / "data"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(ENV_DATA_DIR / "metadata.json", "r", encoding="utf-8") as f:
        template_metadata = json.load(f)
    with open(ENV_DATA_DIR / "branch_migration_seed.json", "r", encoding="utf-8") as f:
        seed = json.load(f)

    core = seed["asn_map"]["core"]
    east_hub = seed["asn_map"]["east_hub"]
    west_hub = seed["asn_map"]["west_hub"]
    branch_den = seed["asn_map"]["branch_den"]
    branch_phx = seed["asn_map"]["branch_phx"]
    branch_sea = seed["asn_map"]["branch_sea"]
    branch_bos = seed["asn_map"]["branch_bos"]

    topology = {
        "connections": [
            {"from": core, "to": east_hub},
            {"from": core, "to": west_hub},
            {"from": east_hub, "to": branch_den},
            {"from": east_hub, "to": branch_phx},
            {"from": west_hub, "to": branch_sea},
            {"from": west_hub, "to": branch_bos},
            {"from": east_hub, "to": west_hub},
            {"from": west_hub, "to": east_hub},
        ]
    }

    route = {
        "prefix": seed["route"]["prefix"],
        "origin_asn": branch_bos,
        "branch_id": seed["route"]["branch_id"],
        "description": seed["route"]["description"],
    }

    preferences = {
        str(east_hub): {
            "prefer_via": west_hub,
            "description": "East hub prefers migrated branch traffic via west hub",
        },
        str(west_hub): {
            "prefer_via": east_hub,
            "description": "West hub prefers migrated branch traffic via east hub",
        },
    }

    relationships = [
        {"from": core, "to": east_hub, "type": "provider"},
        {"from": core, "to": west_hub, "type": "provider"},
        {"from": east_hub, "to": core, "type": "customer"},
        {"from": west_hub, "to": core, "type": "customer"},
        {"from": east_hub, "to": branch_den, "type": "provider"},
        {"from": east_hub, "to": branch_phx, "type": "provider"},
        {"from": west_hub, "to": branch_sea, "type": "provider"},
        {"from": west_hub, "to": branch_bos, "type": "provider"},
        {"from": branch_den, "to": east_hub, "type": "customer"},
        {"from": branch_phx, "to": east_hub, "type": "customer"},
        {"from": branch_sea, "to": west_hub, "type": "customer"},
        {"from": branch_bos, "to": west_hub, "type": "customer"},
        {"from": east_hub, "to": west_hub, "type": "peer"},
        {"from": west_hub, "to": east_hub, "type": "peer"},
    ]

    local_pref = {
        "customer": 200,
        "peer": 100,
        "provider": 50,
        "description": "Standard BGP local preference weights for branch transit reasoning",
    }

    route_events = [
        {
            "advertiser_asn": east_hub,
            "source_asn": core,
            "destination_asn": west_hub,
            "source_type": "provider",
            "destination_type": "peer",
            "branch_id": seed["route"]["branch_id"],
            "prefix": seed["route"]["prefix"],
            "description": "East hub advertises a provider-learned branch route to its peer west hub during migration",
        }
    ]

    migration_context = {
        "template_name": template_metadata["itemDisplayName"],
        "migration_wave": "wave-2",
        "hub_regions": {
            "east_hub": "East US",
            "west_hub": "West Europe",
        },
        "branch_states": [
            {"branch_id": "branch-den", "attached_hub_asn": east_hub, "state": "steady"},
            {"branch_id": "branch-phx", "attached_hub_asn": east_hub, "state": "steady"},
            {"branch_id": "branch-sea", "attached_hub_asn": west_hub, "state": "steady"},
            {"branch_id": "branch-bos", "attached_hub_asn": west_hub, "state": "migrating"},
        ],
        "notes": seed["notes"],
    }

    candidate_fixes = list(seed["candidate_fixes"])
    random.seed(17)
    random.shuffle(candidate_fixes)

    outputs = {
        "topology.json": topology,
        "route.json": route,
        "preferences.json": preferences,
        "relationships.json": relationships,
        "local_pref.json": local_pref,
        "route_events.json": route_events,
        "candidate_fixes.json": candidate_fixes,
        "migration_context.json": migration_context,
    }

    for name, payload in outputs.items():
        with open(DATA_DIR / name, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)


if __name__ == "__main__":
    main()
