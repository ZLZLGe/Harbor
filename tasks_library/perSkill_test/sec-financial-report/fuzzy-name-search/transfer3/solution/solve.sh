#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import re
import subprocess


fund_script = "/root/.codex/skills/fuzzy-name-search/scripts/search_fund.py"
stock_script = "/root/.codex/skills/fuzzy-name-search/scripts/search_stock_cusip.py"
source = open("/root/data/mixed_queries.md", encoding="utf-8").read().splitlines()

rows = []
mode = None
for line in source:
    line = line.strip()
    if not line:
        continue
    if line == "## Funds":
        mode = "fund"
        continue
    if line == "## Stocks":
        mode = "stock"
        continue
    if not line.startswith("- "):
        continue
    value = line[2:]
    if mode == "fund":
        quarter, alias = [part.strip() for part in value.split("|", 1)]
        stdout = subprocess.check_output(
            ["python3", fund_script, "--keywords", alias, "--quarter", quarter, "--topk", "1"],
            text=True,
        )
        accession = re.search(r"ACCESSION_NUMBER:\s*([0-9-]+)", stdout)
        name = re.search(r"FILINGMANAGER_NAME:\s*(.+)", stdout)
        if not accession or not name:
            raise RuntimeError(f"Could not parse fund result from output:\n{stdout}")
        rows.append(("fund", alias, quarter, accession.group(1).strip(), name.group(1).strip()))
    elif mode == "stock":
        alias = value.strip()
        stdout = subprocess.check_output(
            ["python3", stock_script, "--keywords", alias, "--topk", "1"],
            text=True,
        )
        cusip = re.search(r"CUSIP:\s*([A-Z0-9]+)", stdout)
        name = re.search(r"Name:\s*(.+)", stdout)
        if not cusip or not name:
            raise RuntimeError(f"Could not parse stock result from output:\n{stdout}")
        rows.append(("stock", alias, "-", cusip.group(1).strip(), name.group(1).strip()))

with open("/root/watchlist_resolution.tsv", "w", encoding="utf-8") as fh:
    fh.write("kind\tquery\tquarter\tresolved_id\tresolved_name\n")
    for row in rows:
        fh.write("\t".join(row) + "\n")
PY
