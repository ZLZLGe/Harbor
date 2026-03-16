#!/usr/bin/env python3
"""Generate the Azure Route Server NVA containment dataset."""

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

    with open(ENV_DATA_DIR / "route_server_seed.json", "r", encoding="utf-8") as f:
        seed = json.load(f)

    ars = seed["asn_map"]["route_server"]
    nva_a = seed["asn_map"]["nva_a"]
    nva_b = seed["asn_map"]["nva_b"]
    spoke_app = seed["asn_map"]["spoke_app"]
    spoke_ops = seed["asn_map"]["spoke_ops"]
    spoke_pay = seed["asn_map"]["spoke_pay"]
    spoke_analytics = seed["asn_map"]["spoke_analytics"]

    topology = {
        "connections": [
            {"from": ars, "to": nva_a},
            {"from": ars, "to": nva_b},
            {"from": nva_a, "to": ars},
            {"from": nva_b, "to": ars},
            {"from": nva_a, "to": spoke_app},
            {"from": nva_a, "to": spoke_ops},
            {"from": nva_b, "to": spoke_pay},
            {"from": nva_b, "to": spoke_analytics},
            {"from": nva_a, "to": nva_b},
            {"from": nva_b, "to": nva_a},
        ]
    }

    route = {
        "prefix": seed["route"]["prefix"],
        "origin_asn": spoke_analytics,
        "origin_vnet": seed["route"]["origin_vnet"],
        "route_server": seed["deployment"]["route_server_name"],
        "description": seed["route"]["description"],
    }

    preferences = {
        str(nva_a): {
            "prefer_via": nva_b,
            "description": "NVA-A prefers the analytics spoke prefix via NVA-B transit",
        },
        str(nva_b): {
            "prefer_via": nva_a,
            "description": "NVA-B prefers the analytics spoke prefix via NVA-A transit",
        },
    }

    relationships = [
        {"from": ars, "to": nva_a, "type": "provider"},
        {"from": ars, "to": nva_b, "type": "provider"},
        {"from": nva_a, "to": ars, "type": "customer"},
        {"from": nva_b, "to": ars, "type": "customer"},
        {"from": nva_a, "to": spoke_app, "type": "provider"},
        {"from": nva_a, "to": spoke_ops, "type": "provider"},
        {"from": nva_b, "to": spoke_pay, "type": "provider"},
        {"from": nva_b, "to": spoke_analytics, "type": "provider"},
        {"from": spoke_app, "to": nva_a, "type": "customer"},
        {"from": spoke_ops, "to": nva_a, "type": "customer"},
        {"from": spoke_pay, "to": nva_b, "type": "customer"},
        {"from": spoke_analytics, "to": nva_b, "type": "customer"},
        {"from": nva_a, "to": nva_b, "type": "peer"},
        {"from": nva_b, "to": nva_a, "type": "peer"},
    ]

    local_pref = {
        "customer": 200,
        "peer": 100,
        "provider": 50,
        "description": "Standard BGP local preference weights for Azure Route Server service insertion",
    }

    route_events = [
        {
            "advertiser_asn": nva_a,
            "source_asn": ars,
            "destination_asn": nva_b,
            "source_type": "provider",
            "destination_type": "peer",
            "prefix": seed["route"]["prefix"],
            "origin_asn": spoke_analytics,
            "route_server": seed["deployment"]["route_server_name"],
            "description": "NVA-A re-advertises an Azure Route Server-learned spoke prefix to its NVA peer",
        }
    ]

    deployment_context = {
        "route_server_name": seed["deployment"]["route_server_name"],
        "route_server_region": seed["deployment"]["route_server_region"],
        "transit_vnet": seed["deployment"]["transit_vnet"],
        "spokes": seed["deployment"]["spokes"],
        "nva_roles": [
            {"name": "nva-a", "asn": nva_a, "role": "active inspection"},
            {"name": "nva-b", "asn": nva_b, "role": "standby inspection"},
        ],
        "notes": seed["notes"],
    }

    candidate_mitigations = list(seed["candidate_mitigations"])
    random.seed(23)
    random.shuffle(candidate_mitigations)

    outputs = {
        "topology.json": topology,
        "route.json": route,
        "preferences.json": preferences,
        "relationships.json": relationships,
        "local_pref.json": local_pref,
        "route_events.json": route_events,
        "candidate_mitigations.json": candidate_mitigations,
        "deployment_context.json": deployment_context,
    }

    for name, payload in outputs.items():
        with open(DATA_DIR / name, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)


if __name__ == "__main__":
    main()
