Implement a parser that converts `/app/incident_triage_handbook.md` into a structured incident decision graph JSON at `/app/incident_triage_map.json` and a DOT visualization at `/app/incident_triage_map.dot`.

The handbook starts with ordinary markdown notes, then uses bracketed section headers for incident states:

```text
# Release War Room Handbook

[AlertIngress]
Monitor: PagerDuty reports elevated 5xx after the deploy wave. -> SeverityGate

[SeverityGate]
1. [SEV-1] Checkout is fully down. -> SevOneBridge
2. Error rate is elevated but transactions still succeed. -> SevTwoAssess
```

Your parser should preserve:

- each bracketed section header as the node `id`
- speaker and spoken text for alert, triage, communications, database, and recovery nodes
- full numbered option text for decision edges, including bracketed labels such as `[Rollback]`, `[Feature Flag]`, or `[Vendor Escalation]`
- escalation loops, re-check paths, rollback paths, and terminal recovery conclusions

Output JSON must use this shape:

```json
{
  "nodes": [
    {"id": "AlertIngress", "text": "...", "speaker": "Monitor", "type": "line"},
    {"id": "SeverityGate", "text": "", "speaker": "", "type": "choice"}
  ],
  "edges": [
    {"from": "AlertIngress", "to": "SeverityGate", "text": ""},
    {"from": "SeverityGate", "to": "SevOneBridge", "text": "1. [SEV-1] Checkout is fully down."}
  ]
}
```

Please implement `def parse_script(text: str)` in `solution.py`. It should return the parsed graph as either a dictionary or an object that can be serialized into the schema above.

Constraints:

1. All nodes must be reachable from the first bracketed section in the file.
2. All edge targets must exist, except for the terminal target `End`.
3. The output must preserve severity escalation, rollback and mitigation branches, stabilization re-check loops, and the distinct final incident outcomes.
4. The output must reflect the provided handbook content rather than a hardcoded graph.
