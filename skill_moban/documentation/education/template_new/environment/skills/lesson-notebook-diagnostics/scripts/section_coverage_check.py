from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat


REQUIRED = [
    "What we're analyzing",
    "Understand the event data",
    "Build the session funnel",
    "Compare quiz outcomes",
    "Spot metric definition traps",
    "Practice",
    "Wrap up",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: section_coverage_check.py <notebook-path>", file=sys.stderr)
        return 2

    nb = nbformat.read(Path(sys.argv[1]), as_version=4)
    headings = []
    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        for line in cell.source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(stripped.lstrip("#").strip())

    positions = {name: None for name in REQUIRED}
    for idx, heading in enumerate(headings):
        if heading in positions and positions[heading] is None:
            positions[heading] = idx

    report = {
        "headings_found": headings,
        "positions": positions,
        "missing": [name for name, pos in positions.items() if pos is None],
        "in_order": all(
            positions[REQUIRED[i]] is not None
            and positions[REQUIRED[i + 1]] is not None
            and positions[REQUIRED[i]] < positions[REQUIRED[i + 1]]
            for i in range(len(REQUIRED) - 1)
        ),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
