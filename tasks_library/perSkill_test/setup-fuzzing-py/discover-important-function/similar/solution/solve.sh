#!/bin/bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

repos = {
    "recordframe": {
        "target": "recordframe.parser.parse_record_stream",
        "risk": "length-prefixed bytes that branch on separators and decode boundaries",
        "tests": "existing tests already check malformed separators and ValueError behavior",
    },
    "tokenmesh": {
        "target": "tokenmesh.messages.parse_mesh_packet",
        "risk": "user-controlled token counts and alias expansion make parser boundaries easy to mutate",
        "tests": "current tests confirm short payloads should raise ValueError",
    },
    "yamlishconf": {
        "target": "yamlishconf.loader.load_document",
        "risk": "line-oriented config parsing mixes comments, delimiters, and scalar coercion",
        "tests": "existing tests show malformed lines are supposed to fail loudly",
    },
}

base = Path("/root/repos")
libraries = sorted(repos)
(base / "libraries.txt").write_text("\n".join(libraries) + "\n", encoding="utf-8")

for repo_name, meta in repos.items():
    notes = [
        f"target function: {meta['target']}",
        f"risk summary: {meta['risk']}",
        f"test oracle hint: {meta['tests']}",
    ]
    (base / repo_name / "notes_for_testing.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
PY
