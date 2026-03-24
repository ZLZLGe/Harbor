Implement a parser that converts `/app/return_playbook.txt` into a structured workflow graph JSON at `/app/warranty_returns_flow.json` and a DOT visualization at `/app/warranty_returns_flow.dot`.

The input uses the same general script format as the source task:

```text
[NodeId]
Speaker: Dialogue text. -> NextNode

[ChoiceNode]
1. Customer option text. -> NextNode
2. [Tagged] Policy or routing option. -> NextNode
```

Your parser should preserve:

- each node header as the node `id`
- speaker and spoken text for service, policy, routing, and agent dialogue nodes
- full numbered option text for customer choices, including bracketed policy labels such as `[Within 30 Days]`
- transfer-to-human steps and all terminal resolution branches

Output JSON must use this shape:

```json
{
  "nodes": [
    {"id": "Start", "text": "...", "speaker": "Assistant", "type": "line"},
    {"id": "IntentMenu", "text": "", "speaker": "", "type": "choice"}
  ],
  "edges": [
    {"from": "Start", "to": "IntentMenu", "text": ""},
    {"from": "IntentMenu", "to": "HumanQueue", "text": "4. Speak to a returns specialist now."}
  ]
}
```

Please implement `def parse_script(text: str)` in `solution.py`. It should return the parsed graph as either a dictionary or an object that can be serialized into the schema above.

Constraints:

1. All nodes must be reachable from the first node in the file.
2. All edge targets must exist, except for the terminal target `End`.
3. The output must accurately represent automated resolutions, transfer-to-human routing, and closed or denied branches.
4. The output must reflect the provided playbook rather than a hardcoded graph.
