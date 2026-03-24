import csv
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/resolved_placeholders.tsv")

EXPECTED_HEADER = [
    "note_id",
    "section",
    "resolved_title",
    "resolved_authors",
    "year",
    "venue",
    "canonical_identifier",
]

EXPECTED_ROWS = [
    {
        "note_id": "RV-01",
        "section": "backbone-history",
        "resolved_title": "Deep Residual Learning for Image Recognition",
        "resolved_authors": "Kaiming He; Xiangyu Zhang; Shaoqing Ren; Jian Sun",
        "year": "2016",
        "venue": "CVPR",
        "canonical_identifier": "10.1109/CVPR.2016.90",
    },
    {
        "note_id": "RV-02",
        "section": "feature-reuse",
        "resolved_title": "Densely Connected Convolutional Networks",
        "resolved_authors": "Gao Huang; Zhuang Liu; Laurens van der Maaten; Kilian Q. Weinberger",
        "year": "2017",
        "venue": "CVPR",
        "canonical_identifier": "10.1109/CVPR.2017.243",
    },
    {
        "note_id": "RV-03",
        "section": "instance-segmentation",
        "resolved_title": "Mask R-CNN",
        "resolved_authors": "Kaiming He; Georgia Gkioxari; Piotr Dollar; Ross Girshick",
        "year": "2017",
        "venue": "ICCV",
        "canonical_identifier": "10.1109/ICCV.2017.322",
    },
    {
        "note_id": "RV-04",
        "section": "dense-detection",
        "resolved_title": "Focal Loss for Dense Object Detection",
        "resolved_authors": "Tsung-Yi Lin; Priya Goyal; Ross Girshick; Kaiming He; Piotr Dollar",
        "year": "2017",
        "venue": "ICCV",
        "canonical_identifier": "10.1109/ICCV.2017.324",
    },
]


def load_output():
    assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"
    with OUTPUT_FILE.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return reader.fieldnames, list(reader)


class TestOutputStructure:
    def test_output_exists(self):
        assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"

    def test_header_matches_exactly(self):
        header, _ = load_output()
        assert header == EXPECTED_HEADER, "TSV header does not match the required schema"

    def test_row_count(self):
        _, rows = load_output()
        assert len(rows) == 4, f"Expected 4 resolved rows, found {len(rows)}"

    def test_each_line_is_tab_separated(self):
        lines = OUTPUT_FILE.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            assert line.count("\t") == 6, f"Line {index} is not a 7-column TSV row"


class TestResolvedContent:
    def test_exact_rows_match(self):
        _, rows = load_output()
        assert rows == EXPECTED_ROWS, "Resolved placeholder rows do not match the expected papers"

    def test_rows_sorted_by_note_id(self):
        _, rows = load_output()
        note_ids = [row["note_id"] for row in rows]
        assert note_ids == sorted(note_ids), "Rows must be sorted by note_id"

    def test_ambiguous_note_not_included(self):
        _, rows = load_output()
        note_ids = {row["note_id"] for row in rows}
        assert "RV-05" not in note_ids, "Ambiguous placeholder RV-05 should be skipped"

    def test_required_fields_non_empty(self):
        _, rows = load_output()
        for row in rows:
            for field in EXPECTED_HEADER:
                assert row[field].strip(), f"Field {field} must not be empty for {row['note_id']}"

    def test_text_fields_are_clean(self):
        _, rows = load_output()
        for row in rows:
            assert "{" not in row["resolved_title"], f"Title still contains braces: {row['resolved_title']}"
            assert "\\" not in row["resolved_title"], f"Title still contains escape characters: {row['resolved_title']}"
            assert "\\" not in row["resolved_authors"], f"Authors still contain escape characters: {row['resolved_authors']}"

    def test_identifiers_are_dois(self):
        _, rows = load_output()
        for row in rows:
            assert row["canonical_identifier"].startswith("10."), f"Expected DOI-like identifier for {row['note_id']}"

    def test_years_are_four_digits(self):
        _, rows = load_output()
        for row in rows:
            assert row["year"].isdigit() and len(row["year"]) == 4, f"Invalid year for {row['note_id']}"
