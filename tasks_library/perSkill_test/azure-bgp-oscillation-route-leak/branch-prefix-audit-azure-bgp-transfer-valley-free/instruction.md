Audit the Azure VPN branch advertisement evidence in `/app/data/` and write a per-prefix valley-free compliance report.

Available inputs:
- `branch_inventory.json`: branch sites, attached hubs, ASNs, and audited prefixes
- `relationship_graph.json`: BGP business relationships between Azure transit, hubs, and branches
- `advertisement_paths.json`: observed advertisement steps for the audited prefixes
- `mitigation_catalog.json`: candidate Azure-side changes and the leak paths each one resolves
- `audit_policy.json`: the valley-free rule and the requirements for an acceptable mitigation

What to determine:
1. For each audited prefix, whether the observed advertisement paths are valley-free compliant.
2. For each violating prefix, list every leak path that violates the rule, classify the violation, and identify the ASNs affected by that path.
3. For each prefix, list the mitigation IDs that are acceptable under `audit_policy.json`: Azure-supported, policy-level, connectivity-preserving, and sufficient to cover every leak path for that prefix.

Write `/app/output/branch_prefix_audit.json` in this format:

```json
{
  "audit_summary": {
    "audited_prefix_count": 4,
    "violating_prefixes": ["172.16.10.0/24", "172.16.30.0/24"],
    "clean_prefixes": ["172.16.20.0/24"],
    "total_leak_paths": 3
  },
  "prefix_audits": [
    {
      "prefix": "172.16.10.0/24",
      "origin_site": "retail-east",
      "origin_asn": 65321,
      "attached_hub_asn": 65302,
      "valley_free_compliant": false,
      "leak_paths": [
        {
          "path_id": "path-101",
          "classification": "provider_to_peer",
          "leaker_asn": 65303,
          "learned_from_asn": 65301,
          "exported_to_asn": 65304,
          "affected_asns": [65301, 65303, 65304, 65321]
        }
      ],
      "acceptable_mitigation_ids": ["mit-02", "mit-05"]
    }
  ]
}
```

Requirements:
- Include every prefix from `branch_inventory.json` exactly once.
- Sort `prefix_audits` by `prefix`.
- Sort each prefix's `leak_paths` by `path_id`.
- Sort `violating_prefixes`, `clean_prefixes`, `acceptable_mitigation_ids`, and every `affected_asns` list in ascending order.
- Only observed paths that are real valley-free violations belong in `leak_paths`.
- If a prefix has no violations, set `leak_paths` and `acceptable_mitigation_ids` to empty lists.
