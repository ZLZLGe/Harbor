Implement a parser that converts `/app/museum_audio_script.txt` into a structured route graph JSON at `/app/museum_audio_route.json` and a DOT visualization at `/app/museum_audio_route.dot`.

The input uses the same general script shape as the source task:

```text
[NodeId]
Speaker: Narration or guide text. -> NextNode

[ChoiceNode]
1. Visitor route choice. -> NextNode
2. [Tagged] Accessibility, replay, or shortcut option. -> NextNode
```

Your parser should preserve:

- each section header as the node `id`
- speaker and spoken text for guide, curator, accessibility, and exhibit narration nodes
- full numbered option text for route choices, including bracketed labels such as `[Replay]` or `[Accessible Map]`
- replay branches, cross-hall shortcuts, and terminal exit paths

Output JSON must use this shape:

```json
{
  "nodes": [
    {"id": "Arrival", "text": "...", "speaker": "Guide", "type": "line"},
    {"id": "LobbyMenu", "text": "", "speaker": "", "type": "choice"}
  ],
  "edges": [
    {"from": "Arrival", "to": "LobbyGreeting", "text": ""},
    {"from": "LobbyMenu", "to": "AccessibilityDesk", "text": "4. [Accessible Map] Request the elevator-friendly route summary."}
  ]
}
```

Please implement `def parse_script(text: str)` in `solution.py`. It should return the parsed graph as either a dictionary or an object that can be serialized into the schema above.

Constraints:

1. All nodes must be reachable from the first node in the file.
2. All edge targets must exist, except for the terminal target `End`.
3. The output must preserve replay options, family or accessibility detours, and the distinct ending routes.
4. The output must reflect the provided museum script rather than a hardcoded graph.
