#!/bin/bash
set -euo pipefail

cat > /tmp/solve_archive_bibliography.py <<'PY'
#!/usr/bin/env python3

import os
import re
from collections import OrderedDict
from pathlib import Path


INPUT_FILE = Path(os.environ.get("ARCHIVE_BIB_INPUT", "/root/archive_catalog_raw.bib"))
OUTPUT_FILE = Path(os.environ.get("ARCHIVE_BIB_OUTPUT", "/root/exhibit_catalog_clean.bib"))

ENTRY_FIELD_ORDER = {
    "article": ["author", "title", "journal", "year", "volume", "number", "pages", "doi"],
    "inproceedings": ["author", "title", "booktitle", "year", "pages", "doi"],
    "book": ["author", "title", "publisher", "year", "address", "edition", "isbn"],
}
SUFFIXES = ("Draft", "Copy", "Dup")


def split_entries(text: str) -> list[str]:
    entries = []
    start = None
    depth = 0
    i = 0
    while i < len(text):
        if text[i] == "@":
            start = i
            break
        i += 1
    if start is None:
        return entries

    i = start
    while i < len(text):
        if text[i] == "@":
            start = i
            depth = 0
            while i < len(text):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        entries.append(text[start : i + 1])
                        break
                i += 1
        i += 1
    return entries


def parse_entry(raw: str) -> dict:
    header_match = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,", raw, flags=re.DOTALL)
    if not header_match:
        raise ValueError(f"Cannot parse entry header: {raw[:80]!r}")

    entry_type = header_match.group(1).lower()
    key = header_match.group(2).strip()
    body = raw[header_match.end() :].rstrip().rstrip("}").strip()

    fields = OrderedDict()
    pattern = re.compile(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}\s*,?", flags=re.DOTALL)
    for match in pattern.finditer(body):
        fields[match.group(1).lower()] = " ".join(match.group(2).split())

    return {"type": entry_type, "key": key, "fields": fields}


def normalize_author(value: str) -> str:
    value = value.replace(";", " and ")
    value = value.replace(" & ", " and ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_pages(value: str) -> str:
    value = re.sub(r"^pp\.\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"(\d)\s*-\s*(\d)", r"\1--\2", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_doi(value: str) -> str:
    value = value.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.strip()


def normalize_entry(entry: dict) -> dict:
    fields = OrderedDict()
    allowed_fields = ENTRY_FIELD_ORDER[entry["type"]]
    for field in allowed_fields:
        if field not in entry["fields"]:
            continue
        value = entry["fields"][field]
        if field == "author":
            value = normalize_author(value)
        elif field == "pages":
            value = normalize_pages(value)
        elif field == "doi":
            value = normalize_doi(value)
        fields[field] = value
    return {"type": entry["type"], "key": entry["key"], "fields": fields}


def key_penalty(key: str) -> int:
    return 1 if key.endswith(SUFFIXES) else 0


def select_better(existing: dict, candidate: dict) -> dict:
    existing_score = (key_penalty(existing["key"]), -len(existing["fields"]), existing["key"])
    candidate_score = (key_penalty(candidate["key"]), -len(candidate["fields"]), candidate["key"])
    return candidate if candidate_score < existing_score else existing


def format_entry(entry: dict) -> str:
    lines = [f'@{entry["type"]}{{{entry["key"]},']
    ordered_fields = ENTRY_FIELD_ORDER[entry["type"]]
    width = max(len(field) for field in ordered_fields)
    for field in ordered_fields:
        if field in entry["fields"]:
            lines.append(f'  {field.ljust(width)} = {{{entry["fields"][field]}}},')
    lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    raw_text = INPUT_FILE.read_text(encoding="utf-8")
    entries = [normalize_entry(parse_entry(chunk)) for chunk in split_entries(raw_text)]

    deduped: OrderedDict[str, dict] = OrderedDict()
    unique_without_doi = []
    for entry in entries:
        doi = entry["fields"].get("doi", "")
        if doi:
            if doi in deduped:
                deduped[doi] = select_better(deduped[doi], entry)
            else:
                deduped[doi] = entry
        else:
            unique_without_doi.append(entry)

    final_entries = list(deduped.values()) + unique_without_doi
    final_entries.sort(key=lambda item: item["key"].lower())
    output = "\n\n".join(format_entry(entry) for entry in final_entries) + "\n"
    OUTPUT_FILE.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_archive_bibliography.py
