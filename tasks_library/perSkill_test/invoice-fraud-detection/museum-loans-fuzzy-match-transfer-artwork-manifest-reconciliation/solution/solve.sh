#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import re
from difflib import SequenceMatcher


CATALOG_PATH = "/root/approved_loans_catalog.tsv"
MANIFEST_PATH = "/root/shipping_manifest.ndjson"
OUTPUT_PATH = "/root/loan_manifest_flags.ndjson"


def normalize_title(text: str) -> str:
    text = text.lower()
    text = text.replace("&", " and ")
    text = text.replace("'", "").replace("’", "")
    text = re.sub(r"[():;,.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def full_title_variant(text: str) -> str:
    return normalize_title(text)


def base_title_variant(text: str) -> str:
    text = re.sub(r"\([^)]*\)", "", text)
    parts = re.split(r"\s[-–—]\s|:|;", text, maxsplit=1)
    return normalize_title(parts[0])


def title_score(left: str, right: str) -> float:
    left_variants = {full_title_variant(left), base_title_variant(left)}
    right_variants = {full_title_variant(right), base_title_variant(right)}
    return max(SequenceMatcher(None, a, b).ratio() * 100 for a in left_variants for b in right_variants)


with open(CATALOG_PATH, encoding="utf-8", newline="") as handle:
    catalog = list(csv.DictReader(handle, delimiter="\t"))

with open(MANIFEST_PATH, encoding="utf-8") as handle:
    manifest_rows = [json.loads(line) for line in handle if line.strip()]


flagged_rows = []

for row in manifest_rows:
    scored = []
    for record in catalog:
        scored.append((title_score(row["shipped_artwork_title"], record["approved_title"]), record))
    scored.sort(key=lambda item: item[0], reverse=True)

    best_score, best_record = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else float("-inf")

    output_row = {
        "manifest_line_id": row["manifest_line_id"],
        "crate_id": row["crate_id"],
        "shipped_artwork_title": row["shipped_artwork_title"],
        "matched_catalog_id": None,
        "matched_catalog_title": None,
        "borrowing_institution": row["borrowing_institution"],
        "insurance_policy_number": row["insurance_policy_number"],
        "reason": None,
    }

    if best_score < 88 or best_score - second_score < 4:
        output_row["reason"] = "Unmatched Artwork"
        flagged_rows.append(output_row)
        continue

    output_row["matched_catalog_id"] = best_record["catalog_id"]
    output_row["matched_catalog_title"] = best_record["approved_title"]

    if row["borrowing_institution"] != best_record["approved_borrowing_institution"]:
        output_row["reason"] = "Borrowing Institution Mismatch"
        flagged_rows.append(output_row)
        continue

    if row["insurance_policy_number"] != best_record["approved_policy_number"]:
        output_row["reason"] = "Insurance Policy Mismatch"
        flagged_rows.append(output_row)
        continue


with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    for item in flagged_rows:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
PY
