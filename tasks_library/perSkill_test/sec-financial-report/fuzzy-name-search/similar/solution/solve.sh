#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import subprocess


def run(cmd):
    return subprocess.check_output(cmd, text=True)


def parse_accession(stdout):
    match = re.search(r"ACCESSION_NUMBER:\s*([0-9-]+)", stdout)
    if not match:
        raise RuntimeError(f"Could not parse accession number from output:\n{stdout}")
    return match.group(1)


def parse_cusip(stdout):
    match = re.search(r"CUSIP:\s*([A-Z0-9]+)", stdout)
    if not match:
        raise RuntimeError(f"Could not parse CUSIP from output:\n{stdout}")
    return match.group(1)


skill_root = "/root/.codex/skills/fuzzy-name-search/scripts"

answers = {
    "q3_manager_accession": parse_accession(
        run(["python3", f"{skill_root}/search_fund.py", "--keywords", "renaisance technolgies", "--quarter", "2025-q3", "--topk", "1"])
    ),
    "q2_manager_accession": parse_accession(
        run(["python3", f"{skill_root}/search_fund.py", "--keywords", "berkshire hathawy", "--quarter", "2025-q2", "--topk", "1"])
    ),
    "palantir_cusip": parse_cusip(
        run(["python3", f"{skill_root}/search_stock_cusip.py", "--keywords", "palantir techologies", "--topk", "1"])
    ),
    "microstrategy_cusip": parse_cusip(
        run(["python3", f"{skill_root}/search_stock_cusip.py", "--keywords", "micro stratagy", "--topk", "1"])
    ),
}

with open("/root/fuzzy_lookup_answers.json", "w", encoding="utf-8") as fh:
    json.dump(answers, fh, indent=2)
PY
