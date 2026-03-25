#!/bin/bash
set -euo pipefail

python - <<'PY'
import ast
from pathlib import Path

root = Path("/root/repos/mailpiece/mailpiece")
file_scores = []
function_scores = []

for py_file in sorted(root.glob("*.py")):
    code = py_file.read_text(encoding="utf-8")
    score = sum(code.count(keyword) for keyword in ("parse", "load", "decode", "boundary"))
    file_scores.append((score, py_file.name))
    module = ast.parse(code)
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            fn_score = score + sum(node.name.count(token) for token in ("parse", "load", "decode"))
            function_scores.append((fn_score, f"mailpiece.{py_file.stem}.{node.name}", py_file.name))

lines = ["# mailpiece fuzz target report", "", "Top files:"]
for score, filename in sorted(file_scores, reverse=True):
    lines.append(f"- {filename}: score={score}")

lines.extend(["", "Top functions:"])
for score, qualname, filename in sorted(function_scores, reverse=True)[:4]:
    lines.append(f"- {qualname} ({filename}) score={score}")

lines.extend(
    [
        "",
        "Shortlist:",
        "- mailpiece.parser.parse_message: public entry point that coordinates header and multipart parsing",
        "- mailpiece.headers.parse_headers: line-oriented boundary parser with strict delimiter checks",
        "- mailpiece.parts.parse_boundary_section: multipart section splitter keyed off attacker-controlled boundary strings",
    ]
)

Path("/root/transfer1_APIs.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
