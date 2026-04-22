from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: notebook_lint.py <notebook-path>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    nb = nbformat.read(path, as_version=4)

    markdown_cells = [cell for cell in nb.cells if cell.cell_type == "markdown"]
    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]
    headings = [
        line.strip("# ").strip()
        for cell in markdown_cells
        for line in cell.source.splitlines()
        if line.lstrip().startswith("#")
    ]
    report = {
        "path": str(path),
        "cell_count": len(nb.cells),
        "markdown_cells": len(markdown_cells),
        "code_cells": len(code_cells),
        "heading_count": len(headings),
        "headings": headings,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
