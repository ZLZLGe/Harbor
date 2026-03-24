#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
ENV_ROOT = Path(__file__).resolve().parent
SEED_FILE = ENV_ROOT / "data" / "failover_seed.json"
DATA_DIR = APP_ROOT / "data"


def write_json(name: str, payload: object) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / name, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def main() -> None:
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        seed = json.load(f)

    azure_asn = seed["azure_edge"]["asn"]
    er_asn = seed["expressroute_gateway"]["asn"]
    vpn_asn = seed["vpn_gateway"]["asn"]
    branch_chi = seed["branches"][0]["asn"]
    branch_den = seed["branches"][1]["asn"]
    branch_hou = seed["branches"][2]["asn"]
    prefix = seed["prefix"]

    topology = {
        "connections": [
            {"from": azure_asn, "to": er_asn},
            {"from": azure_asn, "to": vpn_asn},
            {"from": er_asn, "to": azure_asn},
            {"from": vpn_asn, "to": azure_asn},
            {"from": er_asn, "to": branch_chi},
            {"from": branch_chi, "to": er_asn},
            {"from": vpn_asn, "to": branch_den},
            {"from": branch_den, "to": vpn_asn},
            {"from": vpn_asn, "to": branch_hou},
            {"from": branch_hou, "to": vpn_asn},
            {"from": er_asn, "to": vpn_asn},
            {"from": vpn_asn, "to": er_asn},
        ]
    }

    preferences = {
        str(er_asn): {
            "prefer_via": vpn_asn,
            "description": "The ExpressRoute edge prefers the branch-hou prefix through the VPN peer during failover."
        },
        str(vpn_asn): {
            "prefer_via": er_asn,
            "description": "The VPN edge also prefers the same branch-hou prefix back through the ExpressRoute peer."
        },
    }

    relationships = [
        {"from": azure_asn, "to": er_asn, "type": "provider"},
        {"from": azure_asn, "to": vpn_asn, "type": "provider"},
        {"from": er_asn, "to": azure_asn, "type": "customer"},
        {"from": vpn_asn, "to": azure_asn, "type": "customer"},
        {"from": er_asn, "to": branch_chi, "type": "provider"},
        {"from": branch_chi, "to": er_asn, "type": "customer"},
        {"from": vpn_asn, "to": branch_den, "type": "provider"},
        {"from": branch_den, "to": vpn_asn, "type": "customer"},
        {"from": vpn_asn, "to": branch_hou, "type": "provider"},
        {"from": branch_hou, "to": vpn_asn, "type": "customer"},
        {"from": er_asn, "to": vpn_asn, "type": "peer"},
        {"from": vpn_asn, "to": er_asn, "type": "peer"},
    ]

    local_pref = {
        "customer": 200,
        "peer": 100,
        "provider": 50,
        "description": "Standard local preference weights for a hybrid ExpressRoute and VPN failover design."
    }

    route = {
        "prefix": prefix,
        "origin_asn": branch_hou,
        "origin_branch": seed["branches"][2]["name"],
        "incident_id": seed["incident_id"],
        "description": "Branch-hou prefix that should stay primary on ExpressRoute while VPN remains backup-only."
    }

    route_events = [
        {
            "advertiser_asn": er_asn,
            "source_asn": azure_asn,
            "destination_asn": vpn_asn,
            "source_type": "provider",
            "destination_type": "peer",
            "prefix": prefix,
            "origin_asn": branch_hou,
            "path_label": "ExpressRoute-to-VPN backup peer",
            "description": "The ExpressRoute customer edge re-advertises an Azure-edge-learned branch route to the VPN failover peer."
        }
    ]

    incident_context = {
        "incident_id": seed["incident_id"],
        "azure_region": seed["azure_region"],
        "azure_edge": seed["azure_edge"],
        "expressroute_gateway": seed["expressroute_gateway"],
        "vpn_gateway": seed["vpn_gateway"],
        "branches": seed["branches"],
        "allowed_control_points": [
            "customer-edge routing policy",
            "AS-PATH or community-based filtering on customer edges",
            "user defined routes on Azure subnets",
        ],
        "notes": seed["notes"],
    }

    write_json("topology.json", topology)
    write_json("preferences.json", preferences)
    write_json("relationships.json", relationships)
    write_json("local_pref.json", local_pref)
    write_json("route.json", route)
    write_json("route_events.json", route_events)
    write_json("candidate_remediations.json", seed["candidate_remediations"])
    write_json("incident_context.json", incident_context)


if __name__ == "__main__":
    main()
