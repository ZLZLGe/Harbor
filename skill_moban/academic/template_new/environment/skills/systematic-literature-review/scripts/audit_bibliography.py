#!/usr/bin/env python3
import csv
import json
import os
import re
from pathlib import Path

import bibtexparser

from _catalog import load_records
from _record_logic import is_eligible
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
CANDIDATES_PATH = WORKSPACE_ROOT / "data" / "candidate_records.csv"
BIB_PATH = WORKSPACE_ROOT / "references.bib"


def normalize_text(value: str) -> str:
    value = value or ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.removeprefix("https://doi.org/")
    value = value.removeprefix("http://doi.org/")
    value = value.removeprefix("doi:")
    return value


def flatten_reference(entry: dict) -> dict[str, str]:
    authors = entry.get("author", "") or entry.get("authors", "")
    title = entry.get("title", "")
    journal = entry.get("journal", "") or entry.get("journaltitle", "")
    return {
        "key": entry.get("ID", ""),
        "title": title,
        "journal": journal,
        "year": str(entry.get("year", "")).strip(),
        "doi": normalize_doi(str(entry.get("doi", "")).strip()),
        "author": authors,
    }


with CANDIDATES_PATH.open("r", encoding="utf-8", newline="") as handle:
    candidate_ids = [row["study_id"] for row in csv.DictReader(handle)]

with BIB_PATH.open("r", encoding="utf-8") as handle:
    references = bibtexparser.load(handle).entries

records = load_records(candidate_ids)
target_ids = [study_id for study_id, record in records.items() if is_eligible(record)]
expected_metadata = {
    study_id: {
        "doi": normalize_doi(record["doi"]),
        "title": record["title"],
        "journal": record["journal"],
        "year": str(record["year"]),
        "first_author_last_name": record["short_citation"].split()[0].lower(),
    }
    for study_id, record in records.items()
    if study_id in target_ids
}

flattened = [flatten_reference(reference) for reference in references]
matched_by_study: dict[str, list[dict[str, str]]] = {study_id: [] for study_id in target_ids}
extra_entries: list[str] = []

for entry in flattened:
    matched_id = None
    for study_id, expected in expected_metadata.items():
        if entry["doi"] and entry["doi"] == expected["doi"]:
            matched_id = study_id
            break
        if normalize_text(entry["title"]) == normalize_text(expected["title"]):
            matched_id = study_id
            break
    if matched_id is None:
        extra_entries.append(entry["key"] or entry["title"] or "<untitled>")
        continue
    matched_by_study[matched_id].append(entry)

field_repairs: dict[str, dict[str, str]] = {}
missing_entries: list[str] = []
multiple_matches: list[str] = []

for study_id, expected in expected_metadata.items():
    matches = matched_by_study.get(study_id, [])
    if not matches:
        missing_entries.append(study_id)
        field_repairs[study_id] = expected
        continue
    if len(matches) > 1:
        multiple_matches.append(study_id)
    observed = matches[0]
    mismatches = {}
    if observed["doi"] != expected["doi"]:
        mismatches["doi"] = expected["doi"]
    if normalize_text(observed["title"]) != normalize_text(expected["title"]):
        mismatches["title"] = expected["title"]
    if observed["year"] != expected["year"]:
        mismatches["year"] = expected["year"]
    if normalize_text(observed["journal"]) != normalize_text(expected["journal"]):
        mismatches["journal"] = expected["journal"]
    if expected["first_author_last_name"] not in normalize_text(observed["author"]):
        mismatches["first_author_last_name"] = expected["first_author_last_name"]
    if mismatches:
        field_repairs[study_id] = mismatches

print(
    json.dumps(
        {
            "target_study_ids": target_ids,
            "missing_entries": missing_entries,
            "multiple_matches": multiple_matches,
            "extra_entries": extra_entries,
            "field_repairs": field_repairs,
            "reference_targets": expected_metadata,
        },
        indent=2,
        ensure_ascii=False,
    )
)
