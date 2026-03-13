from __future__ import annotations

import os
import re
from pathlib import Path


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "assembled_references.bib"

EXPECTED_ORDER = [
    "Doudna2014genome",
    "Joshi2017triviaqa",
    "Vaswani2017attention",
    "Watson1953molecular",
]

EXPECTED = {
    "Doudna2014genome": {
        "ENTRYTYPE": "article",
        "title": "Genome editing. The new frontier of genome engineering with CRISPR-Cas9",
        "journal": "Science",
        "year": "2014",
        "volume": "346",
        "number": "6213",
        "pages": "1258096",
        "doi": "10.1126/science.1258096",
        "url": "https://doi.org/10.1126/science.1258096",
        "note_contains": "pmid: 25430774",
        "author_families": ["Doudna", "Charpentier"],
    },
    "Joshi2017triviaqa": {
        "ENTRYTYPE": "inproceedings",
        "title": "TriviaQA: A Large Scale Distantly Supervised Challenge Dataset for Reading Comprehension",
        "booktitle": "Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
        "year": "2017",
        "pages": "1601--1611",
        "doi": "10.18653/v1/P17-1147",
        "url": "https://doi.org/10.18653/v1/P17-1147",
        "author_families": ["Joshi", "Choi", "Weld", "Zettlemoyer"],
    },
    "Vaswani2017attention": {
        "ENTRYTYPE": "misc",
        "title": "Attention Is All You Need",
        "year": "2017",
        "url": "https://arxiv.org/abs/1706.03762",
        "note_contains": "arxiv:1706.03762",
        "author_families": ["Vaswani", "Shazeer", "Parmar", "Uszkoreit", "Jones", "Gomez", "Kaiser", "Polosukhin"],
    },
    "Watson1953molecular": {
        "ENTRYTYPE": "article",
        "title": "Molecular Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic Acid",
        "journal": "Nature",
        "year": "1953",
        "volume": "171",
        "number": "4356",
        "pages": "737--738",
        "doi": "10.1038/171737a0",
        "url": "https://doi.org/10.1038/171737a0",
        "author_families": ["Watson", "Crick"],
    },
}


def normalize_text(value: str) -> str:
    value = value.replace("\\", "")
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def read_braced(text: str, start: int) -> tuple[str, int]:
    if text[start] != "{":
        raise AssertionError(f"Expected '{{' at position {start}")
    depth = 0
    index = start
    buffer = []
    while index < len(text):
        char = text[index]
        if char == "{":
            depth += 1
            if depth > 1:
                buffer.append(char)
        elif char == "}":
            depth -= 1
            if depth == 0:
                return "".join(buffer), index + 1
            buffer.append(char)
        else:
            buffer.append(char)
        index += 1
    raise AssertionError("Unterminated braced value in BibTeX output")


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    length = len(body)

    while index < length:
        while index < length and body[index] in " \t\r\n,":
            index += 1
        if index >= length:
            break

        name_start = index
        while index < length and (body[index].isalnum() or body[index] in "_-"):
            index += 1
        field_name = body[name_start:index].lower()
        while index < length and body[index].isspace():
            index += 1
        if index >= length or body[index] != "=":
            raise AssertionError(f"Malformed field assignment near: {body[name_start:name_start + 40]!r}")
        index += 1
        while index < length and body[index].isspace():
            index += 1

        if index < length and body[index] == "{":
            value, index = read_braced(body, index)
        else:
            value_start = index
            while index < length and body[index] not in ",\n":
                index += 1
            value = body[value_start:index]

        fields[field_name] = value.strip()
        while index < length and body[index].isspace():
            index += 1
        if index < length and body[index] == ",":
            index += 1

    return fields


def parse_bibtex(text: str) -> list[dict[str, str]]:
    entries = []
    index = 0
    length = len(text)

    while index < length:
        at_index = text.find("@", index)
        if at_index == -1:
            break

        type_start = at_index + 1
        type_end = type_start
        while type_end < length and (text[type_end].isalnum() or text[type_end] in "_-"):
            type_end += 1
        entry_type = text[type_start:type_end].lower()
        if type_end >= length or text[type_end] != "{":
            raise AssertionError(f"Malformed BibTeX entry near position {at_index}")

        body, next_index = read_braced(text, type_end)
        comma_index = body.find(",")
        if comma_index == -1:
            raise AssertionError(f"Missing key separator in entry body: {body[:60]!r}")

        key = body[:comma_index].strip()
        fields = parse_fields(body[comma_index + 1 :])
        fields["ENTRYTYPE"] = entry_type
        fields["ID"] = key
        entries.append(fields)
        index = next_index

    return entries


def assert_author_field(author_field: str, expected_families: list[str]) -> None:
    author_parts = [part.strip() for part in author_field.split(" and ") if part.strip()]
    assert len(author_parts) == len(expected_families), (
        f"Author count mismatch. Expected {len(expected_families)}, found {len(author_parts)} in {author_field!r}"
    )
    for expected_family, author_part in zip(expected_families, author_parts):
        assert normalize_text(expected_family) in normalize_text(author_part), (
            f"Missing expected author family {expected_family!r} in {author_part!r}"
        )


def main() -> None:
    assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"
    raw_text = OUTPUT_FILE.read_text(encoding="utf-8")
    assert raw_text.strip(), "Output file is empty"

    entries = parse_bibtex(raw_text)
    assert len(entries) == 4, f"Expected 4 BibTeX entries after deduplication, found {len(entries)}"

    keys = [entry["ID"] for entry in entries]
    assert keys == EXPECTED_ORDER, f"Unexpected citation key order: {keys}"

    unique_titles = {normalize_text(entry["title"]) for entry in entries}
    assert len(unique_titles) == 4, "Found duplicate titles in assembled_references.bib"

    entries_by_key = {entry["ID"]: entry for entry in entries}
    assert set(entries_by_key) == set(EXPECTED), f"Unexpected key set: {sorted(entries_by_key)}"

    for key, expected in EXPECTED.items():
        entry = entries_by_key[key]
        assert entry["ENTRYTYPE"] == expected["ENTRYTYPE"], (
            f"{key} should be @{expected['ENTRYTYPE']}, found @{entry['ENTRYTYPE']}"
        )
        assert normalize_text(entry.get("title", "")) == normalize_text(expected["title"]), (
            f"Title mismatch for {key}: {entry.get('title', '')!r}"
        )
        assert_author_field(entry.get("author", ""), expected["author_families"])
        assert entry.get("year", "") == expected["year"], f"Year mismatch for {key}"

        for field_name in ("journal", "booktitle", "volume", "number", "pages", "url"):
            if field_name in expected:
                assert entry.get(field_name, "") == expected[field_name], (
                    f"Field {field_name!r} mismatch for {key}: {entry.get(field_name, '')!r}"
                )

        if "doi" in expected:
            doi_value = entry.get("doi", "")
            assert doi_value == expected["doi"], f"DOI mismatch for {key}: {doi_value!r}"
            assert not doi_value.startswith("https://doi.org/"), f"DOI field for {key} must be a bare DOI"

        if "note_contains" in expected:
            assert expected["note_contains"] in normalize_text(entry.get("note", "")), (
                f"Missing note content for {key}: {entry.get('note', '')!r}"
            )

    for key in ("Joshi2017triviaqa", "Watson1953molecular"):
        assert "--" in entries_by_key[key]["pages"], f"Page range for {key} must use double hyphen"

    print("All BibTeX checks passed.")


if __name__ == "__main__":
    main()
