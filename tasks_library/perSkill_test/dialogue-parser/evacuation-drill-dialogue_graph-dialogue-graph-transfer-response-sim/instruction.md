You will implement a parser that converts a building evacuation drill response script into a structured JSON decision graph and a DOT visualization. The input file is `/app/evacuation_drill_script.txt`, and you must write `/app/evacuation_response.json` plus `/app/evacuation_response.dot`.

Implement your parser in `solution.py`. Include a function `def parse_script(text: str)` that returns a dictionary with the shape `{"nodes": [...], "edges": [...]}`.

The script format uses section headers like `[NodeId]`. A section with a single line in the form `Speaker: Text -> Target` should become a node with:

- `id`: the section name
- `text`: the spoken text
- `speaker`: the speaker name
- `type`: `"line"`

and a plain edge `{"from": "<section>", "to": "<target>", "text": ""}`.

A section with numbered options like `1. Dispatch the stair-chair team. -> StairChairDeploy` should become a node with:

- `id`: the section name
- `text`: `""`
- `speaker`: `""`
- `type`: `"choice"`

and one edge per option whose `text` preserves the exact option label, including bracketed tags such as `[Fallback]`.

The parser must support:

- line nodes and choice nodes
- broadcast prompts, team handoffs, and role-based responses
- fallback loops that return to earlier coordination hubs
- multiple edges that end at `End`
- validation that every non-`End` edge target exists
- validation that every node is reachable from the first section in the file

The DOT file must describe the same graph, use directed edges, and render choice nodes as diamonds.
