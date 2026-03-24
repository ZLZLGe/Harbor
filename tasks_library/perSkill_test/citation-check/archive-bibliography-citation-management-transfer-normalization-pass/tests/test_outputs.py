import os
import re
from pathlib import Path

import bibtexparser
import pytest

ANSWER_FILE = Path(os.environ.get("ARCHIVE_BIB_OUTPUT", "/root/exhibit_catalog_clean.bib"))

EXPECTED_ORDER = [
    "Clark2019cataloguing",
    "Liu2021archiveInterfaces",
    "Mendes2020preservation",
    "Roberts2022finding",
    "Singh2023metadata",
]

EXPECTED_FIELDS = {
    "Clark2019cataloguing": ["author", "title", "journal", "year", "volume", "number", "pages", "doi"],
    "Liu2021archiveInterfaces": ["author", "title", "booktitle", "year", "pages", "doi"],
    "Mendes2020preservation": ["author", "title", "publisher", "year", "address", "edition", "isbn"],
    "Roberts2022finding": ["author", "title", "booktitle", "year", "pages", "doi"],
    "Singh2023metadata": ["author", "title", "journal", "year", "volume", "number", "pages", "doi"],
}

EXPECTED_ENTRIES = {
    "Clark2019cataloguing": {
        "ENTRYTYPE": "article",
        "author": "Clark, Mara and Ortega, Julian",
        "title": "Cataloguing Ephemeral Print in Community Archives",
        "journal": "Journal of Archival Practice",
        "year": "2019",
        "volume": "14",
        "number": "2",
        "pages": "11--24",
        "doi": "10.1080/01930826.2019.1583011",
    },
    "Liu2021archiveInterfaces": {
        "ENTRYTYPE": "inproceedings",
        "author": "Liu, Wen and Alvarez, Sofia",
        "title": "Designing Archive Interfaces for Object-Rich Collections",
        "booktitle": "Proceedings of the Joint Conference on Digital Libraries",
        "year": "2021",
        "pages": "77--89",
        "doi": "10.1145/3469624.3476895",
    },
    "Mendes2020preservation": {
        "ENTRYTYPE": "book",
        "author": "Mendes, Helena and Nasser, Omar",
        "title": "Preservation Workflows for Small Exhibition Catalogs",
        "publisher": "Rivergate Press",
        "year": "2020",
        "address": "Lisbon",
        "edition": "2",
        "isbn": "978-1-916700-45-2",
    },
    "Roberts2022finding": {
        "ENTRYTYPE": "inproceedings",
        "author": "Roberts, Elise and Khan, Tariq and Mendez, Lucia",
        "title": "Finding Stable Citation Keys in Digitization Pipelines",
        "booktitle": "Proceedings of the ACM/IEEE Joint Conference on Digital Libraries",
        "year": "2022",
        "pages": "301--312",
        "doi": "10.18653/v1/2022.jcdl-main.31",
    },
    "Singh2023metadata": {
        "ENTRYTYPE": "article",
        "author": "Priya Singh and Alex Moreno",
        "title": "Metadata Drift and Repair in Traveling Exhibitions",
        "journal": "Archival Science",
        "year": "2023",
        "volume": "38",
        "number": "1",
        "pages": "88--101",
        "doi": "10.1177/03400352231124567",
    },
}

EXCLUDED_KEYS = {"Clark2019cataloguingDraft", "Roberts2022findingDup"}


def load_db():
    assert ANSWER_FILE.exists(), f"Missing output file: {ANSWER_FILE}"
    with ANSWER_FILE.open(encoding="utf-8") as handle:
        return bibtexparser.load(handle)


def read_text():
    assert ANSWER_FILE.exists(), f"Missing output file: {ANSWER_FILE}"
    return ANSWER_FILE.read_text(encoding="utf-8")


def get_entry_block(text: str, citation_key: str) -> str:
    pattern = rf"@\w+\{{{re.escape(citation_key)},\n(.*?)\n\}}"
    match = re.search(pattern, text, flags=re.DOTALL)
    assert match, f"Could not find entry block for {citation_key}"
    return match.group(1)


class TestOutputExists:
    def test_output_exists(self):
        assert ANSWER_FILE.exists(), f"Missing output file: {ANSWER_FILE}"

    def test_output_not_empty(self):
        assert ANSWER_FILE.exists(), f"Missing output file: {ANSWER_FILE}"
        assert ANSWER_FILE.read_text(encoding="utf-8").strip()


class TestBibtexContent:
    def test_parses_as_bibtex(self):
        db = load_db()
        assert len(db.entries) == 5

    def test_entry_order(self):
        text = read_text()
        actual_order = re.findall(r"@\w+\{([^,]+),", text)
        assert actual_order == EXPECTED_ORDER

    def test_duplicate_keys_removed(self):
        db = load_db()
        actual_keys = {entry["ID"] for entry in db.entries}
        assert actual_keys.isdisjoint(EXCLUDED_KEYS)

    def test_no_extra_entries(self):
        db = load_db()
        actual_keys = sorted(entry["ID"] for entry in db.entries)
        assert actual_keys == sorted(EXPECTED_ORDER)


class TestNormalizedMetadata:
    @pytest.mark.parametrize("citation_key", EXPECTED_ORDER)
    def test_entry_type_and_values(self, citation_key):
        db = load_db()
        entry = next(item for item in db.entries if item["ID"] == citation_key)
        expected = EXPECTED_ENTRIES[citation_key]
        assert entry["ENTRYTYPE"] == expected["ENTRYTYPE"]
        for field, value in expected.items():
            if field == "ENTRYTYPE":
                continue
            assert entry[field] == value

    @pytest.mark.parametrize("citation_key", EXPECTED_ORDER)
    def test_only_expected_fields_present(self, citation_key):
        db = load_db()
        entry = next(item for item in db.entries if item["ID"] == citation_key)
        actual_fields = sorted(key for key in entry.keys() if key not in {"ID", "ENTRYTYPE"})
        assert actual_fields == sorted(EXPECTED_FIELDS[citation_key])

    @pytest.mark.parametrize("citation_key", EXPECTED_ORDER)
    def test_field_order_is_exact(self, citation_key):
        text = read_text()
        block = get_entry_block(text, citation_key)
        actual_field_order = re.findall(r"^\s+(\w+)\s*=", block, flags=re.MULTILINE)
        assert actual_field_order == EXPECTED_FIELDS[citation_key]

    def test_pages_are_normalized(self):
        db = load_db()
        for entry in db.entries:
            if "pages" in entry:
                assert "pp." not in entry["pages"].lower()
                assert "-" not in entry["pages"].replace("--", "")

    def test_dois_are_normalized(self):
        db = load_db()
        for entry in db.entries:
            if "doi" in entry:
                assert not entry["doi"].startswith("https://doi.org/")
                assert not entry["doi"].startswith("http://doi.org/")
                assert not entry["doi"].startswith("doi:")

    def test_removed_fields_do_not_appear(self):
        text = read_text().lower()
        for forbidden in ["note =", "url =", "abstract =", "keywords ="]:
            assert forbidden not in text
