from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat


REQUIRED_SOURCES = [
    "learner_events.csv",
    "metric_definitions.yaml",
    "quiz_items.csv",
]


def practice_section_text(nb: nbformat.NotebookNode) -> str:
    parts: list[str] = []
    in_section = False

    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue

        headings = [line.strip().lstrip("#").strip() for line in cell.source.splitlines() if line.strip().startswith("#")]
        if "Practice" in headings:
            in_section = True
            parts.append(cell.source)
            continue

        if in_section and headings:
            break

        if in_section:
            parts.append(cell.source)

    return "\n".join(parts)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: practice_block_check.py <notebook-path>", file=sys.stderr)
        return 2

    nb = nbformat.read(Path(sys.argv[1]), as_version=4)
    practice_text = practice_section_text(nb)
    practice_lines = [
        line.strip()
        for line in practice_text.splitlines()
        if line.strip() and line.strip() not in {"# Practice", "## Practice", "### Practice"}
    ]
    prompt_like_lines = [
        line
        for line in practice_lines
        if line.endswith("?")
        or line.startswith(("Q1", "Q2", "Q3", "1.", "2.", "3.", "-", "*"))
    ]

    missing_sources = [source for source in REQUIRED_SOURCES if source not in practice_text]
    report = {
        "section_length": len(practice_text.strip()),
        "prompt_like_lines": prompt_like_lines,
        "mentioned_sources": [source for source in REQUIRED_SOURCES if source in practice_text],
        "missing_sources": missing_sources,
        "passed": len(practice_text.strip()) >= 120 and len(prompt_like_lines) >= 3 and not missing_sources,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
