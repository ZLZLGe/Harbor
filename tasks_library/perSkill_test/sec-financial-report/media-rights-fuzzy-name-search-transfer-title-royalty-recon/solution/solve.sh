#!/bin/bash

python3 - <<'PY'
import csv
import json
import os
import re
from collections import defaultdict
from difflib import SequenceMatcher


DATA_ROOT = os.environ.get("TASK_DATA_ROOT", "/root")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/royalty_reconciliation.json")

FUND_TERMS = [
    "bridge water assoc",
    "renaissance tech llc",
]

ISSUER_TERMS = [
    "palantir tech",
    "nvidia corp",
    "micro strat",
]


def normalize(value):
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def best_match(term, choices, key):
    normalized_term = normalize(term)
    ranked = sorted(
        choices,
        key=lambda item: (
            SequenceMatcher(None, normalized_term, normalize(key(item))).ratio(),
            key(item),
        ),
        reverse=True,
    )
    return ranked[0]


def load_tsv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


coverpage = load_tsv(os.path.join(DATA_ROOT, "2025-q2", "COVERPAGE.tsv"))
infotable = load_tsv(os.path.join(DATA_ROOT, "2025-q2", "INFOTABLE.tsv"))

fund_matches = []
target_accessions = []
for term in FUND_TERMS:
    row = best_match(term, coverpage, lambda item: item["FILINGMANAGER_NAME"])
    target_accessions.append(row["ACCESSION_NUMBER"])
    fund_matches.append(
        {
            "search_term": term,
            "accession_number": row["ACCESSION_NUMBER"],
            "filingmanager_name": row["FILINGMANAGER_NAME"],
            "form13f_file_number": row["FORM13FFILENUMBER"],
        }
    )

issuer_catalog = {}
for row in infotable:
    issuer_catalog.setdefault(row["CUSIP"], row["NAMEOFISSUER"])

issuer_rows = [
    {"CUSIP": cusip, "NAMEOFISSUER": issuer_name}
    for cusip, issuer_name in issuer_catalog.items()
]

issuer_matches = []
target_cusips = []
for term in ISSUER_TERMS:
    row = best_match(term, issuer_rows, lambda item: item["NAMEOFISSUER"])
    target_cusips.append(row["CUSIP"])
    issuer_matches.append(
        {
            "search_term": term,
            "cusip": row["CUSIP"],
            "issuer_name": row["NAMEOFISSUER"],
        }
    )

fund_names = {
    row["ACCESSION_NUMBER"]: row["FILINGMANAGER_NAME"]
    for row in coverpage
}

filtered_positions = [
    row
    for row in infotable
    if row["ACCESSION_NUMBER"] in target_accessions and row["CUSIP"] in target_cusips
]

selected_position_summary = {
    "matched_fund_count": len(fund_matches),
    "matched_issuer_count": len(issuer_matches),
    "selected_position_rows": len(filtered_positions),
    "total_value_usd": float(sum(int(row["VALUE_USD"]) for row in filtered_positions)),
}

manager_rollup = defaultdict(lambda: {"total_value_usd": 0, "total_shares": 0, "matched_cusips": set()})
duplicate_groups = defaultdict(list)

for row in filtered_positions:
    accession_number = row["ACCESSION_NUMBER"]
    cusip = row["CUSIP"]
    manager_rollup[accession_number]["total_value_usd"] += int(row["VALUE_USD"])
    manager_rollup[accession_number]["total_shares"] += int(row["SSHPRNAMT"])
    manager_rollup[accession_number]["matched_cusips"].add(cusip)
    duplicate_groups[(accession_number, cusip)].append(row["POSITION_ID"])

manager_exposure_rank = []
for rank, accession_number in enumerate(
    sorted(
        manager_rollup,
        key=lambda item: (-manager_rollup[item]["total_value_usd"], item),
    ),
    start=1,
):
    rollup = manager_rollup[accession_number]
    manager_exposure_rank.append(
        {
            "rank": rank,
            "accession_number": accession_number,
            "filingmanager_name": fund_names[accession_number],
            "total_value_usd": float(rollup["total_value_usd"]),
            "total_shares": rollup["total_shares"],
            "matched_cusips": sorted(rollup["matched_cusips"]),
        }
    )

issuer_names = {row["CUSIP"]: row["NAMEOFISSUER"] for row in issuer_rows}
duplicate_position_groups = []
for accession_number, cusip in sorted(duplicate_groups):
    position_ids = sorted(duplicate_groups[(accession_number, cusip)])
    if len(position_ids) <= 1:
        continue
    duplicate_position_groups.append(
        {
            "accession_number": accession_number,
            "filingmanager_name": fund_names[accession_number],
            "cusip": cusip,
            "issuer_name": issuer_names[cusip],
            "position_ids": position_ids,
            "duplicate_count": len(position_ids),
        }
    )

largest_position_row = sorted(
    filtered_positions,
    key=lambda row: (-int(row["VALUE_USD"]), row["ACCESSION_NUMBER"], row["CUSIP"], row["POSITION_ID"]),
)[0]

result = {
    "fund_matches": fund_matches,
    "issuer_matches": issuer_matches,
    "selected_position_summary": selected_position_summary,
    "manager_exposure_rank": manager_exposure_rank,
    "duplicate_position_groups": duplicate_position_groups,
    "largest_position": {
        "position_id": largest_position_row["POSITION_ID"],
        "accession_number": largest_position_row["ACCESSION_NUMBER"],
        "filingmanager_name": fund_names[largest_position_row["ACCESSION_NUMBER"]],
        "cusip": largest_position_row["CUSIP"],
        "issuer_name": issuer_names[largest_position_row["CUSIP"]],
        "value_usd": float(largest_position_row["VALUE_USD"]),
        "shares": int(largest_position_row["SSHPRNAMT"]),
    },
}

with open(OUTPUT_FILE, "w") as handle:
    json.dump(result, handle, indent=2)
PY
