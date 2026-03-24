Inspect the hybrid ExpressRoute and VPN failover incident data in `/app/data/` and write `/app/output/failover_leak_review.json`.

Input files:
- `topology.json`: directed BGP adjacencies for the Azure edge, paired gateways, and branch sites
- `preferences.json`: gateway failover preferences for the affected branch prefix
- `relationships.json`: BGP relationship type for each directed edge
- `local_pref.json`: standard local-preference weights
- `route.json`: the branch prefix involved in the incident
- `route_events.json`: observed propagation events for that prefix
- `candidate_remediations.json`: candidate mitigation actions to assess
- `incident_context.json`: gateway names, Azure-managed constraints, and branch notes

Required analysis:
1. Detect whether the gateway preference graph contains a cycle. If it does, return the sorted gateway ASNs in that cycle and the same ASNs in `affected_gateways`.
2. Detect upstream route leaks using valley-free logic. Treat these as leaks:
   - a route learned from a provider exported to a peer or provider
   - a route learned from a peer exported to a peer or provider
3. Evaluate every candidate remediation from `candidate_remediations.json`.
   - Reject connectivity-destruction actions such as disabling gateway peerings, shutting down connections, or attaching custom route maps directly to Azure-managed gateways.
   - For allowed actions, decide whether the action breaks the gateway preference cycle and whether it stops the upstream route leak.
   - Score each action with this rubric:
     - `100` if the action is allowed and fixes both issues
     - `60` if the action is allowed and fixes exactly one issue
     - `20` if the action is allowed but fixes neither issue
     - `0` if the action is forbidden
4. Save JSON with this structure:

```json
{
  "failover_cycle_detected": true,
  "failover_cycle": [65310, 65311],
  "affected_gateways": [65310, 65311],
  "upstream_route_leak_detected": true,
  "upstream_route_leaks": [
    {
      "leaker_as": 65310,
      "source_as": 65300,
      "destination_as": 65311,
      "source_type": "provider",
      "destination_type": "peer",
      "prefix": "10.88.30.0/24",
      "origin_asn": 65330,
      "path_label": "ExpressRoute-to-VPN backup peer"
    }
  ],
  "remediation_assessments": {
    "candidate remediation text": {
      "allowed": true,
      "breaks_cycle": false,
      "stops_leak": true,
      "score": 60
    }
  },
  "forbidden_actions": [
    "forbidden remediation text"
  ]
}
```

Ordering requirements:
- Return `forbidden_actions` sorted in ascending alphabetical order by the full remediation text.
