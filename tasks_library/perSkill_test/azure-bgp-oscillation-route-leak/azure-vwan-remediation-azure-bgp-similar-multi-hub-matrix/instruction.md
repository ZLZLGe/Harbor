Analyze the Azure Virtual WAN incident described in `/app/data/` and decide which candidate changes actually remediate the control-plane problems.

Available inputs:
- `deployment_snapshot.json`: regional hub and spoke inventory for the incident
- `topology_bundle.json`: BGP adjacencies, AS relationships, preferred next hops, and the two customer prefixes involved
- `leak_observations.json`: observed route leak events that already happened
- `candidate_changes.json`: proposed remediation actions to evaluate

What to determine:
1. Whether the preferred-next-hop graph contains a BGP oscillation cycle, and if so which ASNs are in that cycle.
2. Which leak observations are real valley-free violations.
3. For every candidate change, whether it is a viable Azure-side remediation, whether it breaks the preference cycle, and which leak observations it resolves.

Write `/app/output/multi_hub_remediation_matrix.json` in this format:

```json
{
  "analysis_summary": {
    "oscillation_detected": true,
    "preference_cycle": [65102, 65103, 65104],
    "leak_ids": ["leak-001", "leak-002"],
    "affected_prefixes": ["10.44.10.0/24", "10.55.20.0/24"]
  },
  "remediation_matrix": [
    {
      "candidate_id": "chg-01",
      "candidate_change": "Increase BGP keepalive and hold timers on all three virtual hubs",
      "azure_viable": false,
      "breaks_preference_cycle": false,
      "resolved_leak_ids": [],
      "remaining_leak_ids": ["leak-001", "leak-002"],
      "overall_effect": "no_fix"
    }
  ]
}
```

Requirements:
- Include every candidate from `candidate_changes.json` exactly once.
- Sort `remediation_matrix` by `candidate_id`.
- `resolved_leak_ids` and `remaining_leak_ids` must also be sorted.
- Use only the evidence in the provided files. Timer tuning, restarts, or removing hub connectivity are not real remediations for this incident.
