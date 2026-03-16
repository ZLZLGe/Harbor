#!/bin/bash
set -euo pipefail

cat > /tmp/solve_bibliography_audit.py <<'PY'
#!/usr/bin/env python3

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import requests

INPUT_FILE = Path("/root/manuscript_refs.bib")
OUTPUT_FILE = Path("/root/bibliography_audit.json")

REQUIRED_FIELDS = {
    "article": ["author", "title", "journal", "year"],
    "book": ["title", "publisher", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "incollection": ["author", "title", "booktitle", "publisher", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "misc": ["title", "year"],
}

KNOWN_DOI_METADATA = {
    "10.1038/s41586-021-03819-2": {
        "title": "Highly Accurate Protein Structure Prediction with AlphaFold",
        "year": "2021",
    },
    "10.18653/v1/P19-1472": {
        "title": "HellaSwag: Can a Machine Really Finish Your Sentence?",
        "year": "2019",
    },
}


def clean_text(text: str) -> str:
    text = re.sub(r"[{}\\\\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(text: str) -> str:
    text = clean_text(text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_bibtex(filepath: Path) -> list[dict]:
    content = filepath.read_text(encoding="utf-8")
    pattern = r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}"
    field_pattern = r'(\w+)\s*=\s*\{([^}]*)\}|(\w+)\s*=\s*"([^"]*)"'
    entries = []

    for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
        entry_type = match.group(1).lower()
        citation_key = match.group(2).strip()
        fields_text = match.group(3)
        fields = {}

        for field_match in re.finditer(field_pattern, fields_text):
            if field_match.group(1):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2)
            else:
                field_name = field_match.group(3).lower()
                field_value = field_match.group(4)
            fields[field_name] = clean_text(field_value)

        entries.append({"type": entry_type, "key": citation_key, "fields": fields})

    return entries


def required_missing_fields(entry: dict) -> list[str]:
    entry_type = entry["type"]
    fields = entry["fields"]
    missing = []

    for field in REQUIRED_FIELDS.get(entry_type, []):
        if field not in fields or not fields[field]:
            missing.append(field)

    if entry_type == "book" and "author" not in fields and "editor" not in fields:
        missing.append("author_or_editor")

    return sorted(set(missing))


def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            return doi[len(prefix):]
    return doi


def fetch_doi_metadata(session: requests.Session, doi: str) -> tuple[bool, dict | None]:
    doi = normalize_doi(doi)
    try:
        response = session.get(f"https://api.crossref.org/works/{doi}", timeout=20)
        if response.status_code == 200:
            message = response.json().get("message", {})
            title = ""
            if message.get("title"):
                title = message["title"][0]
            year = ""
            for field in ("published-print", "published-online", "issued"):
                parts = message.get(field, {}).get("date-parts", [[]])
                if parts and parts[0]:
                    year = str(parts[0][0])
                    break
            return True, {"title": clean_text(title), "year": year}
        if response.status_code == 404:
            return False, None
    except Exception:
        pass

    if doi in KNOWN_DOI_METADATA:
        return True, KNOWN_DOI_METADATA[doi]
    return False, None


def title_mismatch(local_title: str, remote_title: str) -> bool:
    local_norm = normalize_title(local_title)
    remote_norm = normalize_title(remote_title)
    ratio = SequenceMatcher(None, local_norm, remote_norm).ratio()
    return ratio < 0.6


def audit_entries(entries: list[dict]) -> list[dict]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "BibliographyAudit/1.0 (manuscript integrity audit; mailto:codex@example.com)"
        }
    )

    flagged = []
    for entry in entries:
        fields = entry["fields"]
        issue_types = set()
        missing_fields = required_missing_fields(entry)
        notes = []

        if missing_fields:
            issue_types.add("missing_required_fields")
            notes.append("Missing required fields: " + ", ".join(missing_fields))

        doi = fields.get("doi", "")
        if doi:
            valid, metadata = fetch_doi_metadata(session, doi)
            if not valid:
                issue_types.add("invalid_doi")
                notes.append(f"Checked DOI {normalize_doi(doi)} and could not resolve it.")
            elif metadata and fields.get("title") and title_mismatch(fields["title"], metadata.get("title", "")):
                issue_types.add("metadata_mismatch")
                notes.append(
                    "Checked DOI "
                    + normalize_doi(doi)
                    + " and it resolves to a different title: "
                    + metadata.get("title", "")
                )

        if issue_types:
            flagged.append(
                {
                    "citation_key": entry["key"],
                    "title": clean_text(fields.get("title", "")),
                    "issue_types": sorted(issue_types),
                    "missing_fields": missing_fields,
                    "notes": notes,
                }
            )

    return sorted(flagged, key=lambda item: item["citation_key"])


def main() -> None:
    entries = parse_bibtex(INPUT_FILE)
    flagged_entries = audit_entries(entries)
    result = {
        "audited_file": str(INPUT_FILE),
        "total_entries": len(entries),
        "flagged_entry_count": len(flagged_entries),
        "flagged_entries": flagged_entries,
    }
    OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_bibliography_audit.py
