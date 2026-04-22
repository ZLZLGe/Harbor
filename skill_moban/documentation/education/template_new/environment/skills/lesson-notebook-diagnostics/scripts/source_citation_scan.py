from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat


KNOWN_SOURCES = [
    "lesson_brief.md",
    "learner_events.csv",
    "quiz_attempts.csv",
    "quiz_items.csv",
    "metric_definitions.yaml",
    "reference_docs/glossary.md",
    "reference_docs/facilitation_notes.md",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: source_citation_scan.py <notebook-path>", file=sys.stderr)
        return 2

    nb = nbformat.read(Path(sys.argv[1]), as_version=4)
    text = "\n".join(cell.source for cell in nb.cells)
    report = {
        "mentioned_sources": [source for source in KNOWN_SOURCES if source in text],
        "missing_sources": [source for source in KNOWN_SOURCES if source not in text],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
