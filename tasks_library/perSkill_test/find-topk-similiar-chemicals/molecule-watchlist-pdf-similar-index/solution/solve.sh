#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
import json
import re
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader

pdf_path = Path("/root/data/inspection_catalog")
watchlist_path = Path("/root/data/watchlist.txt")
output_path = Path("/root/workspace/watchlist_hits.json")

watchlist = [line.strip() for line in watchlist_path.read_text(encoding="utf-8").splitlines() if line.strip()]
pattern = re.compile(r"^Entry\s+\d+:\s*(.+?)\s*$")

occurrences = defaultdict(lambda: defaultdict(list))
reader = PdfReader(str(pdf_path))

for page_number, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ""
    position = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = pattern.match(line)
        if not match:
            continue
        position += 1
        molecule = match.group(1).strip()
        occurrences[molecule][page_number].append(position)

results = []
for molecule in watchlist:
    page_map = occurrences.get(molecule, {})
    pages = sorted(page_map)
    results.append(
        {
            "molecule": molecule,
            "found": bool(pages),
            "pages": pages,
            "occurrence_count": sum(len(items) for items in page_map.values()),
            "page_positions": [
                {"page": page, "positions": page_map[page]}
                for page in pages
            ],
        }
    )

output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
