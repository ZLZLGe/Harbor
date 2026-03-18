Audit the Azure Virtual WAN branch migration inputs in `/app/data/` and produce `/app/output/branch_transit_audit.json`.

Input files:
- `topology.json`: directed AS connectivity for the Virtual WAN core, two hubs, and attached branches
- `preferences.json`: preferred inter-hub next hops
- `relationships.json`: BGP relationship type for each directed edge
- `local_pref.json`: standard local-preference weights
- `route.json`: branch prefix and origin metadata
- `route_events.json`: observed branch route propagation events
- `candidate_fixes.json`: candidate operational or policy changes
- `migration_context.json`: branch migration notes

Required analysis:
1. Detect whether the hub preference graph contains a cycle. If it does, return the sorted hub ASNs in that cycle and the same ASNs in `affected_hubs`.
2. Detect branch route leaks using valley-free logic. Treat these as leaks:
   - a route learned from a provider exported to a peer or provider
   - a route learned from a peer exported to a peer or provider
3. Evaluate every candidate fix from `candidate_fixes.json`.
   - Reject connectivity-teardown actions such as disabling hub connectivity, disabling peering, removing branch connections, or shutting down gateways/connections.
   - For allowed actions, decide whether the action breaks the hub preference cycle and whether it stops the branch route leak.
   - Score each action with this rubric:
     - `100` if the action is allowed and fixes both issues
     - `60` if the action is allowed and fixes exactly one issue
     - `20` if the action is allowed but fixes neither issue
     - `0` if the action is forbidden
4. Save JSON with this structure:

```json
{
  "hub_cycle_detected": true,
  "hub_cycle": [65110, 65111],
  "affected_hubs": [65110, 65111],
  "branch_route_leak_detected": true,
  "branch_route_leaks": [
    {
      "leaker_as": 65110,
      "source_as": 65100,
      "destination_as": 65111,
      "source_type": "provider",
      "destination_type": "peer",
      "branch_id": "branch-bos",
      "prefix": "10.44.8.0/24"
    }
  ],
  "policy_assessments": {
    "candidate action text": {
      "allowed": true,
      "breaks_cycle": false,
      "stops_leak": true,
      "score": 60
    }
  },
  "rejected_forbidden_actions": [
    "forbidden action text"
  ]
}
```
