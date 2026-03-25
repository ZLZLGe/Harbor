#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import subprocess


skill_script = "/root/.codex/skills/fuzzy-name-search/scripts/search_stock_cusip.py"
aliases = json.load(open("/root/data/issuer_watchlist.json", encoding="utf-8"))
results = []

for alias in aliases:
    stdout = subprocess.check_output(
        ["python3", skill_script, "--keywords", alias, "--topk", "1"],
        text=True,
    )
    name = re.search(r"Name:\s*(.+)", stdout)
    cusip = re.search(r"CUSIP:\s*([A-Z0-9]+)", stdout)
    if not name or not cusip:
        raise RuntimeError(f"Could not parse stock result from output:\n{stdout}")
    results.append(
        {
            "alias": alias,
            "issuer_name": name.group(1).strip(),
            "cusip": cusip.group(1).strip(),
        }
    )

with open("/root/issuer_resolution.json", "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2)
PY
