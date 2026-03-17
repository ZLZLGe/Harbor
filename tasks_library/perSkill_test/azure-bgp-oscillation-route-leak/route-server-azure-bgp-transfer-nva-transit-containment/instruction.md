Inspect the Azure Route Server service-insertion dataset in `/app/data/` and write `/app/output/nva_transit_containment.json`.

Input files:
- `topology.json`: directed BGP connectivity for Azure Route Server, paired NVAs, and spoke VNets
- `preferences.json`: NVA next-hop preferences for the protected spoke prefix
- `relationships.json`: BGP relationship type for each directed edge
- `local_pref.json`: standard local-preference weights
- `route.json`: the spoke prefix being propagated through the environment
- `route_events.json`: observed advertisement events for that prefix
- `candidate_mitigations.json`: candidate containment actions
- `deployment_context.json`: Route Server and spoke deployment notes

Required analysis:
1. Detect whether the NVA preference graph contains a cycle. If it does, return the sorted NVA ASNs in that cycle and the same ASNs in `affected_nvas`.
2. Detect provider-route leaks using valley-free logic. Treat these as leaks:
   - a route learned from a provider exported to a peer or provider
   - a route learned from a peer exported to a peer or provider
3. Evaluate every candidate mitigation from `candidate_mitigations.json`.
   - Reject connectivity-destruction actions such as disabling Azure-managed peering, disabling Azure Route Server sessions, removing NVA transit links, or shutting down interfaces.
   - For allowed actions, decide whether the action breaks the NVA preference cycle and whether it stops the provider-route leak.
   - Score each action with this rubric:
     - `100` if the action is allowed and fixes both issues
     - `60` if the action is allowed and fixes exactly one issue
     - `20` if the action is allowed but fixes neither issue
     - `0` if the action is forbidden
4. Save JSON with this structure:

```json
{
  "nva_cycle_detected": true,
  "nva_cycle": [65210, 65211],
  "affected_nvas": [65210, 65211],
  "provider_route_leak_detected": true,
  "provider_route_leaks": [
    {
      "leaker_as": 65210,
      "source_as": 65200,
      "destination_as": 65211,
      "source_type": "provider",
      "destination_type": "peer",
      "prefix": "10.77.32.0/24",
      "origin_asn": 65231,
      "route_server": "ars-prod-eastus"
    }
  ],
  "mitigation_assessments": {
    "candidate mitigation text": {
      "allowed": true,
      "breaks_cycle": false,
      "stops_leak": true,
      "score": 60
    }
  },
  "forbidden_actions": [
    "forbidden action text"
  ]
}
```
