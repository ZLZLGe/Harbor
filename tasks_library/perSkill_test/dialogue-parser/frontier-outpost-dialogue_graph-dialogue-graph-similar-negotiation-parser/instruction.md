You will implement a dialogue parser that converts a frontier outpost negotiation script into a structured JSON graph and a DOT visualization. The input file is `/app/outpost_script.txt`, and you must write `/app/outpost_dialogue.json` plus `/app/outpost_dialogue.dot`.

Implement your parser in `solution.py`. Include a function `def parse_script(text: str)` that returns the parsed graph as a dictionary with the shape `{"nodes": [...], "edges": [...]}`.

The script format uses section headers like `[NodeId]`. A section with a single line in the form `Speaker: Text -> Target` should become a node with:

- `id`: the section name
- `text`: the spoken text
- `speaker`: the speaker name
- `type`: `"line"`

and a plain edge `{"from": "<section>", "to": "<target>", "text": ""}`.

A section with numbered options like `1. [Persuade] Ask for eight days because of the ice road. -> ExtendedDeadline` should become a node with:

- `id`: the section name
- `text`: `""`
- `speaker`: `""`
- `type`: `"choice"`

and one edge per option whose `text` preserves the exact option label, including bracketed skill-check tags.

The parser must support:

- loopbacks to earlier sections
- multiple edges that end at `End`
- both `line` and `choice` nodes
- validation that every non-`End` edge target exists
- validation that every node is reachable from the first section in the file

The DOT file must describe the same graph, use directed edges, and render choice nodes as diamonds.
