#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import re
import subprocess


skill_script = "/root/.codex/skills/fuzzy-name-search/scripts/search_fund.py"
input_path = "/root/data/manager_queries.csv"
output_path = "/root/fund_resolution_table.csv"


def run_search(alias, quarter):
    return subprocess.check_output(
        ["python3", skill_script, "--keywords", alias, "--quarter", quarter, "--topk", "1"],
        text=True,
    )


def parse(stdout, pattern):
    match = re.search(pattern, stdout)
    if not match:
        raise RuntimeError(f"Could not parse pattern {pattern!r} from output:\n{stdout}")
    return match.group(1).strip()


rows = []
with open(input_path, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        stdout = run_search(row["alias"], row["quarter"])
        rows.append(
            {
                "row_id": row["row_id"],
                "quarter": row["quarter"],
                "alias": row["alias"],
                "accession_number": parse(stdout, r"ACCESSION_NUMBER:\s*([0-9-]+)"),
                "manager_name": parse(stdout, r"FILINGMANAGER_NAME:\s*(.+)"),
                "manager_city": parse(stdout, r"FILINGMANAGER_CITY:\s*(.+)"),
                "manager_state": parse(stdout, r"FILINGMANAGER_STATEORCOUNTRY:\s*(.+)"),
            }
        )

with open(output_path, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "row_id",
            "quarter",
            "alias",
            "accession_number",
            "manager_name",
            "manager_city",
            "manager_state",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
