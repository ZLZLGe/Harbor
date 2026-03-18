Implement a parser that converts `/app/drill_playbook.txt` into a structured warehouse drill decision graph JSON at `/app/drill_playbook_graph.json` and a DOT visualization at `/app/drill_playbook_graph.dot`.

The playbook uses the same lightweight section syntax as the source task, but the content is a warehouse safety drill:

```text
[DrillBriefing]
Coordinator: Morning drill begins with a staged report from the outbound warehouse floor. -> ReportIntake

[ReportIntake]
1. [Observe: Smoke] Report light haze near the battery charging cages. -> SmokeObservation
2. [Observe: Spill] Report a leaking solvent drum beside packing lane two. -> SpillObservation
```

Your output JSON must have this shape:

```json
{
  "nodes": [
    {"id": "DrillBriefing", "text": "...", "speaker": "Coordinator", "type": "line"},
    {"id": "ReportIntake", "text": "", "speaker": "", "type": "choice"}
  ],
  "edges": [
    {"from": "DrillBriefing", "to": "ReportIntake", "text": ""},
    {"from": "ReportIntake", "to": "SmokeObservation", "text": "1. [Observe: Smoke] Report light haze near the battery charging cages."}
  ]
}
```

Requirements:

- Preserve every section header as a node ID.
- Use node type `"line"` for coordinator, observer, and team communication steps, and `"choice"` for numbered decision hubs.
- Preserve bracketed drill labels such as `[Observe: Smoke]`, `[Notify: Warehouse Ops]`, `[Escalate: Site Lead]`, and `[Wrap-Up]` in edge text.
- Keep the workflow structure intact. Observation branches feed shared review hubs such as `ReportReview`, `SeverityTriage`, `CleanupPlanning`, and `RecoveryChecklist`.
- Multiple outcomes should terminate through `End`.
- All non-`End` edge targets must exist, and every node must be reachable from the first node in the file.

Place your implementation in `/solution`. The verifier will run `/solution/solve.sh`, and the expected outputs must be written exactly to the paths above.
