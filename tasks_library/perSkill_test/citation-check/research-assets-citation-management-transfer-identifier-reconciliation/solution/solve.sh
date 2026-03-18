#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
from pathlib import Path

INPUT_PATH = Path("/root/research_assets.txt")
SNAPSHOT_PATH = Path("/root/record_snapshot.json")
OUTPUT_PATH = Path("/root/asset_resolution.json")


def normalize_doi(value: str):
    text = value.strip()
    lowered = text.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lowered.startswith(prefix):
            text = text[len(prefix):]
            lowered = text.lower()
            break
    doi_match = re.fullmatch(r"(10\.\S+)", text, flags=re.IGNORECASE)
    if doi_match:
        return doi_match.group(1)
    return None


def normalize_pmid(value: str):
    direct = re.fullmatch(r"pmid[:\s]+(\d+)", value.strip(), flags=re.IGNORECASE)
    if direct:
        return direct.group(1)
    url_match = re.fullmatch(
        r"https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?",
        value.strip(),
        flags=re.IGNORECASE,
    )
    if url_match:
        return url_match.group(1)
    return None


def normalize_arxiv(value: str):
    direct = re.fullmatch(r"arxiv:(\d{4}\.\d{4,5}(?:v\d+)?)", value.strip(), flags=re.IGNORECASE)
    if direct:
        return direct.group(1)
    url_match = re.fullmatch(
        r"https?://arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)",
        value.strip(),
        flags=re.IGNORECASE,
    )
    if url_match:
        return url_match.group(1)
    return None


def normalize_url(value: str):
    stripped = value.strip()
    if re.fullmatch(r"https?://\S+", stripped, flags=re.IGNORECASE):
        return stripped
    return None


with SNAPSHOT_PATH.open(encoding="utf-8") as handle:
    snapshot = json.load(handle)

records = {}
doi_index = {}
pmid_index = {}
arxiv_index = {}
url_index = {}

for record in snapshot:
    canonical_id = record["canonical_id"]
    records[canonical_id] = {
        "canonical_id": canonical_id,
        "title": record["title"],
        "year": record["year"],
        "matched_inputs": [],
        "identifiers": record["identifiers"],
    }
    identifiers = record["identifiers"]
    if identifiers["doi"]:
        doi_index[identifiers["doi"].lower()] = canonical_id
    if identifiers["pmid"]:
        pmid_index[identifiers["pmid"]] = canonical_id
    if identifiers["arxiv"]:
        arxiv_index[identifiers["arxiv"].lower()] = canonical_id
    if identifiers["url"]:
        url_index[identifiers["url"]] = canonical_id

unverified_items = []

for raw_line in INPUT_PATH.read_text(encoding="utf-8").splitlines():
    item = raw_line.strip()
    if not item:
        continue

    canonical_id = None
    doi = normalize_doi(item)
    pmid = normalize_pmid(item)
    arxiv_id = normalize_arxiv(item)
    url = normalize_url(item)

    if doi:
        canonical_id = doi_index.get(doi.lower())
    if canonical_id is None and pmid:
        canonical_id = pmid_index.get(pmid)
    if canonical_id is None and arxiv_id:
        canonical_id = arxiv_index.get(arxiv_id.lower())
    if canonical_id is None and url:
        canonical_id = url_index.get(url)

    if canonical_id is None:
        unverified_items.append({"input": item, "reason": "no_matching_record"})
        continue

    records[canonical_id]["matched_inputs"].append(item)

resolved_records = [
    records[canonical_id]
    for canonical_id in sorted(records)
    if records[canonical_id]["matched_inputs"]
]

payload = {
    "resolved_records": resolved_records,
    "unverified_items": unverified_items,
}

OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
