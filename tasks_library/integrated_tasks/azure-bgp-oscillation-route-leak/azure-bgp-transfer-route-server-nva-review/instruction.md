Review the Azure Route Server and dual-NVA incident data in `/app/data/` and write `/app/output/route_server_reflection_review.json`.

Input files:
- `topology.json`: directed BGP connectivity and ASN labels
- `sessions.json`: Azure Route Server peer session snapshot
- `preferences.json`: per-appliance preferred next hop for the customer prefix under review
- `relationships.json`: BGP relationship type for each directed edge
- `local_pref.json`: default local preference ordering
- `review_context.json`: customer prefix and incident context
- `route_events.json`: observed advertisements that may violate valley-free routing
- `possible_actions.json`: candidate remediations to classify

Requirements:
1. Detect BGP oscillation by finding any preference cycle in `preferences.json`.
2. Use `review_context.json` to identify the customer prefix under review.
3. Use `sessions.json` to determine the Azure Route Server ASN. The ASN is the common `local_as` value for the Route Server peer snapshots.
4. Detect route leaks using valley-free export rules:
   - customer-learned routes may be exported to anyone
   - peer-learned routes may be exported only to customers
   - provider-learned routes may be exported only to customers
5. For every violating event in `route_events.json`, create one `route_leak` incident with:
   - `prefix`
   - `participants`: sorted unique ASN list from `source_as`, `leaker_as`, and `destination_as`
   - `details.leaker_as`
   - `details.source_as`
   - `details.destination_as`
   - `details.source_type`
   - `details.destination_type`
6. If a preference cycle exists, create exactly one `oscillation` incident with:
   - `prefix`: the customer prefix from `review_context.json`
   - `participants`: sorted ASN list for the cycle
   - `details.cycle`: the same sorted ASN list
   - `details.reflected_by`: the Route Server ASN from `sessions.json`
7. Sort `incidents` so the optional `oscillation` incident comes first, then sort all `route_leak` incidents by `(details.leaker_as, details.destination_as, prefix)`.
8. Evaluate every string in `possible_actions.json`.
9. Reject an action if it disables BGP, removes Route Server peering, shuts down connectivity, or only restarts/clears sessions.
10. Use rejection reasons exactly as follows:
   - `prohibited_connectivity_teardown` for disable/remove/shutdown actions
   - `operational_reset_only` for restart or clear-session actions
11. `action_results` must contain every action string. Each value must be:
   - `allowed`: boolean
   - `addresses`: sorted unique list containing zero or more of `oscillation` and `route_leak`
12. `oscillation` is addressed only if the action breaks the customer-prefix preference cycle or pins that customer prefix to a deterministic approved next hop without removing connectivity.
13. `route_leak` is addressed only if the action eliminates every detected valley-free leak, or it combines an approved next-hop change with explicit export suppression so those leaked appliance-to-appliance paths are no longer usable.
14. `effective_changes` must contain every allowed action whose `addresses` list is non-empty, in the same order as `possible_actions.json`.
15. `rejected_actions` must contain every disallowed action in the same order as `possible_actions.json`.

Write exactly this JSON shape:

```json
{
  "review_summary": {
    "customer_prefix": "172.18.44.0/24",
    "route_server_as": 65515,
    "oscillation_detected": true,
    "route_leak_detected": true
  },
  "incidents": [
    {
      "incident_type": "oscillation",
      "prefix": "172.18.44.0/24",
      "participants": [65110, 65111],
      "details": {
        "cycle": [65110, 65111],
        "reflected_by": 65515
      }
    },
    {
      "incident_type": "route_leak",
      "prefix": "0.0.0.0/0",
      "participants": [65110, 65111, 65515],
      "details": {
        "leaker_as": 65110,
        "source_as": 65515,
        "destination_as": 65111,
        "source_type": "provider",
        "destination_type": "peer"
      }
    }
  ],
  "effective_changes": [
    {
      "action": "Apply a symmetric route policy package on nva-east and nva-west: stop preferring customer prefix 172.18.44.0/24 via the opposite appliance and block Route Server-learned prefixes from appliance-to-appliance export",
      "addresses": ["oscillation", "route_leak"]
    }
  ],
  "rejected_actions": [
    {
      "action": "Disable the Route Server BGP peering with nva-west until the incident is over",
      "reason": "prohibited_connectivity_teardown"
    }
  ],
  "action_results": {
    "Apply a symmetric route policy package on nva-east and nva-west: stop preferring customer prefix 172.18.44.0/24 via the opposite appliance and block Route Server-learned prefixes from appliance-to-appliance export": {
      "allowed": true,
      "addresses": ["oscillation", "route_leak"]
    }
  }
}
```
