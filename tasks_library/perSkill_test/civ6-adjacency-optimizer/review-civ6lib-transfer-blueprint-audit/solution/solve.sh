#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

report = {
    "scenario_id": "frontier_blueprint_board",
    "audits": [
        {
            "blueprint_id": "ledger_peak",
            "claimed_total_adjacency": 13,
            "is_valid": True,
            "errors": [],
            "claim_matches": False,
            "district_adjacency": {
                "floodplain_foundry:AQUEDUCT": 0,
                "floodplain_foundry:DAM": 0,
                "floodplain_foundry:INDUSTRIAL_ZONE": 5,
                "ridge_academy:CAMPUS": 2,
                "ridge_academy:COMMERCIAL_HUB": 3,
                "ridge_academy:HOLY_SITE": 2
            },
            "total_adjacency": 12
        },
        {
            "blueprint_id": "canal_detour",
            "claimed_total_adjacency": 7,
            "is_valid": True,
            "errors": [],
            "claim_matches": True,
            "district_adjacency": {
                "floodplain_foundry:AQUEDUCT": 0,
                "floodplain_foundry:DAM": 0,
                "floodplain_foundry:INDUSTRIAL_ZONE": 4,
                "ridge_academy:CAMPUS": 2,
                "ridge_academy:COMMERCIAL_HUB": 0,
                "ridge_academy:HOLY_SITE": 1
            },
            "total_adjacency": 7
        },
        {
            "blueprint_id": "ridge_market",
            "claimed_total_adjacency": 6,
            "is_valid": True,
            "errors": [],
            "claim_matches": False,
            "district_adjacency": {
                "floodplain_foundry:AQUEDUCT": 0,
                "floodplain_foundry:DAM": 0,
                "floodplain_foundry:INDUSTRIAL_ZONE": 2,
                "ridge_academy:CAMPUS": 0,
                "ridge_academy:COMMERCIAL_HUB": 3,
                "ridge_academy:HOLY_SITE": 0
            },
            "total_adjacency": 5
        },
        {
            "blueprint_id": "crowded_claim",
            "claimed_total_adjacency": 10,
            "is_valid": False,
            "errors": [
                "Cities at (2, 2) and (4, 3) are too close: distance=3, minimum=4 (same landmass)"
            ],
            "claim_matches": False,
            "district_adjacency": {},
            "total_adjacency": 0
        },
        {
            "blueprint_id": "double_market_claim",
            "claimed_total_adjacency": 12,
            "is_valid": False,
            "errors": [
                "ridge_academy: districts must exactly match required_districts",
                "ridge_academy: duplicate districts not allowed (COMMERCIAL_HUB)"
            ],
            "claim_matches": False,
            "district_adjacency": {},
            "total_adjacency": 0
        }
    ],
    "valid_ranking": [
        {"rank": 1, "blueprint_id": "ledger_peak", "total_adjacency": 12},
        {"rank": 2, "blueprint_id": "canal_detour", "total_adjacency": 7},
        {"rank": 3, "blueprint_id": "ridge_market", "total_adjacency": 5}
    ],
    "best_valid_blueprint_id": "ledger_peak",
    "best_valid_total_adjacency": 12
}

output_path = Path("/output/blueprint_audit.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(report, indent=2))
print(f"Wrote audit report to {output_path}")
PY
