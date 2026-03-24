Implement a parser that converts `/app/moon_market_script.txt` into a structured dialogue graph JSON at `/app/moon_market_graph.json` and a DOT visualization at `/app/moon_market_graph.dot`.

The input uses the same general format as the source task:

```text
[NodeId]
Speaker: Dialogue text. -> NextNode

[ChoiceNode]
1. Ask a question. -> AskNode
2. [Tagged] Use a special option. -> SpecialNode
```

Your parser should preserve:

- each node header as the node `id`
- speaker and spoken text for dialogue nodes
- full numbered option text for choice edges, including bracketed tags such as `[Charm]`
- branches that loop back to earlier nodes

Output JSON must use this shape:

```json
{
  "nodes": [
    {"id": "MoonMarketStart", "text": "...", "speaker": "Narrator", "type": "line"},
    {"id": "PriceMenu", "text": "", "speaker": "", "type": "choice"}
  ],
  "edges": [
    {"from": "MoonMarketStart", "to": "LanternGreeting", "text": ""},
    {"from": "PriceMenu", "to": "AppraiseLantern", "text": "2. [Appraise] Inspect the lantern frame and crystal seams."}
  ]
}
```

Please implement `def parse_script(text: str)` in `solution.py`. It should return the parsed graph as either a dictionary or an object that can be serialized into the schema above.

Constraints:

1. All nodes must be reachable from the first node in the file.
2. All edge targets must exist, except for the terminal target `End`.
3. The DOT output must visualize choice nodes distinctly and keep bracket-tagged options visually distinguishable from regular options.
4. The output must reflect the provided script content rather than a hardcoded graph.
