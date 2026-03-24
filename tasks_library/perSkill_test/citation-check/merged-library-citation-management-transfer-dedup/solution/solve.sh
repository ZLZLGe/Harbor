#!/bin/bash
set -euo pipefail

cat > /tmp/solve_duplicate_map.py <<'PY'
#!/usr/bin/env python3

import json
import re
from collections import defaultdict
from pathlib import Path


INPUT_FILES = [
    Path("/root/merge_inputs/library_alpha.bib"),
    Path("/root/merge_inputs/library_beta.bib"),
]
OUTPUT_FILE = Path("/root/duplicate_map.json")
COUNTED_FIELDS = (
    "title",
    "author",
    "year",
    "doi",
    "eprint",
    "archiveprefix",
    "journal",
    "booktitle",
    "volume",
    "pages",
    "url",
    "note",
    "howpublished",
)


def clean_text(value: str) -> str:
    value = value.replace("{", "").replace("}", "")
    value = value.replace("\\", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_title(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_key(value: str) -> str:
    return value.strip()


def normalize_year(value: str) -> str:
    match = re.search(r"(19|20)\d{2}", value or "")
    return match.group(0) if match else ""


def normalize_doi(value: str) -> str:
    value = clean_text(value).lower()
    value = value.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    return value.strip()


def normalize_arxiv(entry: dict) -> str:
    candidates = [
        entry["fields"].get("eprint", ""),
        entry["fields"].get("howpublished", ""),
        entry["fields"].get("note", ""),
        entry["fields"].get("url", ""),
    ]
    for candidate in candidates:
        text = clean_text(candidate)
        match = re.search(r"(?:arxiv:|abs/)?(\d{4}\.\d{4,5})(?:v\d+)?", text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def parse_bibtex(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    entries = []
    index = 0
    length = len(text)

    while True:
        start = text.find("@", index)
        if start == -1:
            break

        brace_start = text.find("{", start)
        if brace_start == -1:
            break

        depth = 0
        end = None
        for cursor in range(brace_start, length):
            char = text[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = cursor
                    break

        if end is None:
            raise ValueError(f"Unclosed BibTeX entry in {path}")

        entry_text = text[start : end + 1]
        index = end + 1

        header_match = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,", entry_text, re.DOTALL)
        if not header_match:
            continue

        entry_type = header_match.group(1).strip().lower()
        citation_key = header_match.group(2).strip()
        body = entry_text[header_match.end() : -1]

        fields = {}
        cursor = 0
        while cursor < len(body):
            while cursor < len(body) and body[cursor] in " \t\r\n,":
                cursor += 1
            if cursor >= len(body):
                break

            name_start = cursor
            while cursor < len(body) and (body[cursor].isalnum() or body[cursor] in "_-"):
                cursor += 1
            field_name = body[name_start:cursor].strip().lower()

            while cursor < len(body) and body[cursor].isspace():
                cursor += 1
            if cursor >= len(body) or body[cursor] != "=":
                break
            cursor += 1
            while cursor < len(body) and body[cursor].isspace():
                cursor += 1
            if cursor >= len(body):
                break

            delimiter = body[cursor]
            if delimiter == "{":
                depth = 1
                cursor += 1
                value_start = cursor
                while cursor < len(body) and depth > 0:
                    if body[cursor] == "{":
                        depth += 1
                    elif body[cursor] == "}":
                        depth -= 1
                    cursor += 1
                value = body[value_start : cursor - 1]
            elif delimiter == '"':
                cursor += 1
                value_start = cursor
                while cursor < len(body) and body[cursor] != '"':
                    cursor += 1
                value = body[value_start:cursor]
                cursor += 1
            else:
                value_start = cursor
                while cursor < len(body) and body[cursor] not in ",\n":
                    cursor += 1
                value = body[value_start:cursor]

            fields[field_name] = clean_text(value)

        entries.append(
            {
                "entry_type": entry_type,
                "key": citation_key,
                "fields": fields,
            }
        )

    return entries


def author_last_names(author_field: str) -> list[str]:
    names = []
    for raw_author in re.split(r"\s+and\s+", clean_text(author_field)):
        author = raw_author.strip()
        if not author or author.lower() == "others":
            continue
        if "," in author:
            last = author.split(",", 1)[0]
        else:
            parts = author.split()
            last = parts[-1] if parts else ""
        last = re.sub(r"[^a-z0-9]+", "", last.lower())
        if last:
            names.append(last)
    return names


def title_close(a: str, b: str) -> bool:
    if a == b:
        return True
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
    return overlap >= 0.9


def metadata_score(entry: dict) -> int:
    return sum(1 for field in COUNTED_FIELDS if entry["fields"].get(field))


def build_edges(entries: list[dict]) -> dict[str, set[str]]:
    by_key = {entry["key"]: entry for entry in entries}
    edges = defaultdict(set)

    doi_groups = defaultdict(list)
    arxiv_groups = defaultdict(list)
    title_groups = defaultdict(list)

    for entry in entries:
        doi = normalize_doi(entry["fields"].get("doi", ""))
        if doi:
            doi_groups[doi].append(entry)

        arxiv_id = normalize_arxiv(entry)
        if arxiv_id:
            arxiv_groups[arxiv_id].append(entry)

        title = normalize_title(entry["fields"].get("title", ""))
        year = normalize_year(entry["fields"].get("year", ""))
        if title and year:
            title_groups[(title, year)].append(entry)

    for group in list(doi_groups.values()) + list(arxiv_groups.values()):
        if len(group) < 2:
            continue
        keys = [item["key"] for item in group]
        for left in keys:
            for right in keys:
                if left != right:
                    edges[left].add(right)

    for (_, _), group in title_groups.items():
        if len(group) < 2:
            continue
        for index, left in enumerate(group):
            left_authors = author_last_names(left["fields"].get("author", ""))
            for right in group[index + 1 :]:
                right_authors = author_last_names(right["fields"].get("author", ""))
                overlap = set(left_authors) & set(right_authors)
                same_first_author = bool(left_authors and right_authors and left_authors[0] == right_authors[0])
                if title_close(
                    normalize_title(left["fields"].get("title", "")),
                    normalize_title(right["fields"].get("title", "")),
                ) and (same_first_author or len(overlap) >= 2):
                    edges[left["key"]].add(right["key"])
                    edges[right["key"]].add(left["key"])

    for key in by_key:
        edges.setdefault(key, set())

    return edges


def connected_components(edges: dict[str, set[str]]) -> list[list[str]]:
    seen = set()
    components = []

    for key in edges:
        if key in seen:
            continue
        stack = [key]
        component = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(sorted(edges[current] - seen))
        components.append(sorted(component))

    return components


def main() -> None:
    entries = []
    for path in INPUT_FILES:
        entries.extend(parse_bibtex(path))

    by_key = {entry["key"]: entry for entry in entries}
    edges = build_edges(entries)
    components = connected_components(edges)

    duplicate_map = {}
    for component in components:
        if len(component) < 2:
            continue
        cluster = [by_key[key] for key in component]
        best_score = max(metadata_score(entry) for entry in cluster)
        tied = [entry for entry in cluster if metadata_score(entry) == best_score]
        canonical_key = sorted(entry["key"] for entry in tied)[0]
        merged_keys = sorted(key for key in component if key != canonical_key)
        duplicate_map[canonical_key] = merged_keys

    ordered = {key: duplicate_map[key] for key in sorted(duplicate_map)}
    OUTPUT_FILE.write_text(
        json.dumps({"duplicate_map": ordered}, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_duplicate_map.py
