You will implement a parser that converts an interactive museum audio-route script into a structured JSON graph and a DOT visualization. The input file is `/app/museum_audio_route.txt`, and you must write `/app/museum_route.json` plus `/app/museum_route.dot`.

Implement your parser in `solution.py`. Include a function `def parse_script(text: str)` that returns a dictionary with the shape `{"nodes": [...], "edges": [...]}`.

The script format uses section headers like `[NodeId]`. A section with a single line in the form `Speaker: Text -> Target` should become a node with:

- `id`: the section name
- `text`: the spoken text
- `speaker`: the speaker name
- `type`: `"line"`

and a plain edge `{"from": "<section>", "to": "<target>", "text": ""}`.

A section with numbered options like `1. Enter the fossil gallery. -> FossilIntro` should become a node with:

- `id`: the section name
- `text`: `""`
- `speaker`: `""`
- `type`: `"choice"`

and one edge per option whose `text` preserves the exact option label, including bracketed route tags such as `[Quiet Route]` or `[Family]`.

The parser must support:

- line nodes and choice nodes
- route transfers across different museum wings
- revisit loops back to earlier hubs
- multiple edges that end at `End`
- validation that every non-`End` edge target exists
- validation that every node is reachable from the first section in the file

The DOT file must describe the same graph, use directed edges, and render choice nodes as diamonds.
