#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
export APP_ROOT

python <<'PY'
import json
import os
from collections import defaultdict
from pathlib import Path

app_root = Path(os.environ["APP_ROOT"])
data_dir = app_root / "data"
output_dir = app_root / "output"
output_dir.mkdir(parents=True, exist_ok=True)

inventory = json.loads((data_dir / "branch_inventory.json").read_text())
json.loads((data_dir / "relationship_graph.json").read_text())
paths = json.loads((data_dir / "advertisement_paths.json").read_text())
mitigations = json.loads((data_dir / "mitigation_catalog.json").read_text())
policy = json.loads((data_dir / "audit_policy.json").read_text())

branches_by_prefix = {item["prefix"]: item for item in inventory["branches"]}
violations_by_prefix = defaultdict(list)

for item in paths:
    learned_from = item["learned_from_relationship"]
    exported_to = item["exported_to_relationship"]
    if learned_from in {"provider", "peer"} and exported_to in {"provider", "peer"}:
        branch = branches_by_prefix[item["prefix"]]
        violations_by_prefix[item["prefix"]].append(
            {
                "path_id": item["path_id"],
                "classification": f"{learned_from}_to_{exported_to}",
                "leaker_asn": item["advertiser_asn"],
                "learned_from_asn": item["learned_from_asn"],
                "exported_to_asn": item["exported_to_asn"],
                "affected_asns": sorted(
                    {
                        branch["asn"],
                        item["advertiser_asn"],
                        item["learned_from_asn"],
                        item["exported_to_asn"],
                    }
                ),
            }
        )

requirements = policy["acceptable_mitigation_requirements"]
prefix_audits = []

for branch in sorted(inventory["branches"], key=lambda item: item["prefix"]):
    prefix = branch["prefix"]
    leak_paths = sorted(violations_by_prefix.get(prefix, []), key=lambda item: item["path_id"])
    leak_path_ids = {item["path_id"] for item in leak_paths}

    acceptable_mitigation_ids = []
    if leak_path_ids:
        acceptable_mitigation_ids = sorted(
            mitigation["mitigation_id"]
            for mitigation in mitigations
            if mitigation["azure_supported"] == requirements["azure_supported"]
            and mitigation["policy_level"] == requirements["policy_level"]
            and mitigation["preserves_connectivity"] == requirements["preserves_connectivity"]
            and leak_path_ids.issubset(set(mitigation["resolves_path_ids"]))
        )

    prefix_audits.append(
        {
            "prefix": prefix,
            "origin_site": branch["site"],
            "origin_asn": branch["asn"],
            "attached_hub_asn": branch["attached_hub_asn"],
            "valley_free_compliant": not leak_paths,
            "leak_paths": leak_paths,
            "acceptable_mitigation_ids": acceptable_mitigation_ids,
        }
    )

violating_prefixes = sorted(
    audit["prefix"] for audit in prefix_audits if not audit["valley_free_compliant"]
)
clean_prefixes = sorted(
    audit["prefix"] for audit in prefix_audits if audit["valley_free_compliant"]
)

result = {
    "audit_summary": {
        "audited_prefix_count": len(prefix_audits),
        "violating_prefixes": violating_prefixes,
        "clean_prefixes": clean_prefixes,
        "total_leak_paths": sum(len(audit["leak_paths"]) for audit in prefix_audits),
    },
    "prefix_audits": prefix_audits,
}

(output_dir / "branch_prefix_audit.json").write_text(json.dumps(result, indent=2))
PY
