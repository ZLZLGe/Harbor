Review the Azure Secure Hub incident evidence in `/app/data/` and produce a runbook verdict for the proposed actions.

Available inputs:
- `incident_memo.json`: incident summary, affected hubs, ASNs, and the customer prefix involved
- `topology_snapshot.json`: BGP adjacencies, AS relationships, and preferred next hops between the secure hubs
- `propagation_observations.json`: observed route advertisements during the incident
- `runbook_candidates.json`: candidate runbook steps that operations wants to execute
- `azure_platform_rules.json`: which action types Azure allows and which action types can break the cycle or block the leak

What to determine:
1. Whether the preferred-next-hop graph contains a BGP oscillation cycle, and if so which ASNs are in that cycle.
2. Which propagation observations are real valley-free violations.
3. For every runbook step, whether Azure allows it, whether it breaks the preference cycle, whether it blocks the route leak, and what verdict it should receive.
4. Which allowed step set should be preferred for execution, and which fallback step sets also cover both problems without using forbidden actions.

Write `/app/output/secure_hub_runbook_verdict.json` in this format:

```json
{
  "incident_findings": {
    "oscillation_detected": true,
    "preference_cycle": [65412, 65413],
    "route_leak_detected": true,
    "route_leak_ids": ["obs-401"]
  },
  "step_results": [
    {
      "step_id": "rb-01",
      "title": "Increase BGP keepalive and hold timers on both secure hubs",
      "azure_allowed": false,
      "breaks_preference_cycle": false,
      "blocks_route_leak": false,
      "verdict": "prohibited"
    }
  ],
  "execution_recommendation": {
    "preferred_step_ids": ["rb-06"],
    "fallback_step_sets": [["rb-03", "rb-04"]],
    "avoid_step_ids": ["rb-01"],
    "verdict": "prefer_single_allowed_full_fix"
  }
}
```

Requirements:
- Include every step from `runbook_candidates.json` exactly once.
- Sort `step_results` by `step_id`.
- Sort `route_leak_ids`, `preferred_step_ids`, and `avoid_step_ids` in ascending ID order.
- Sort each fallback set internally and sort `fallback_step_sets` lexicographically by their joined step IDs.
- Only real valley-free violations belong in `route_leak_ids`.
- Timer changes, managed-service restarts, and disabling hub connectivity are not executable incident fixes for this task.
