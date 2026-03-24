import json
from pathlib import Path

import pandas as pd


CATALOG_PATH = Path("/root/catalog_export.csv")
CIRCULATION_PATH = Path("/root/circulation_history.csv")
SCRIPT_PATH = Path("/root/build_merge_candidates.py")
OUTPUT_PATH = Path("/root/catalog_merge_candidates.csv")
SUMMARY_PATH = Path("/root/catalog_merge_summary.json")


def test_required_files_exist():
    assert CATALOG_PATH.exists()
    assert CIRCULATION_PATH.exists()
    assert SCRIPT_PATH.exists(), "build_merge_candidates.py must exist"
    assert OUTPUT_PATH.exists(), "catalog_merge_candidates.csv must exist"
    assert SUMMARY_PATH.exists(), "catalog_merge_summary.json must exist"


def test_input_files_shape():
    catalog = pd.read_csv(CATALOG_PATH, keep_default_na=False)
    circulation = pd.read_csv(CIRCULATION_PATH, keep_default_na=False)

    assert list(catalog.columns) == [
        "record_id",
        "title",
        "author",
        "isbn",
        "format",
        "publication_year",
        "owning_branch",
        "copy_count",
        "audience",
    ]
    assert len(catalog) == 11
    assert set(catalog["format"]) == {"hardcover", "ebook", "paperback", "audiobook"}
    assert (catalog["isbn"] == "").sum() == 3
    assert set(catalog["owning_branch"]) == {"Central", "West", "Digital", "North", "South", "East", "Media"}

    assert list(circulation.columns) == [
        "loan_id",
        "record_id",
        "checkout_date",
        "return_status",
    ]
    assert len(circulation) == 14
    assert circulation["checkout_date"].min() == "2024-11-20"
    assert circulation["checkout_date"].max() == "2025-10-30"


def test_output_columns_and_sort_order():
    output = pd.read_csv(OUTPUT_PATH, keep_default_na=False)

    assert list(output.columns) == [
        "candidate_id",
        "match_basis",
        "normalized_isbn",
        "normalized_title",
        "normalized_author",
        "format",
        "preferred_record_id",
        "merge_record_ids",
        "all_record_ids",
        "member_count",
        "branches_covered",
        "total_copy_count",
        "recent_loan_count",
        "title_variant_count",
        "confidence_reason",
    ]
    assert output["candidate_id"].tolist() == ["MERGE-001", "MERGE-002", "MERGE-003"]
    assert output["match_basis"].tolist() == ["isbn", "isbn", "title_author"]
    assert output["normalized_title"].tolist() == [
        "moby dick",
        "the great gatsby",
        "data science handbook",
    ]


def test_candidate_rows():
    output = pd.read_csv(OUTPUT_PATH, keep_default_na=False)
    records = {row["candidate_id"]: row for row in output.to_dict("records")}

    assert records["MERGE-001"] == {
        "candidate_id": "MERGE-001",
        "match_basis": "isbn",
        "normalized_isbn": "9781501173420",
        "normalized_title": "moby dick",
        "normalized_author": "herman melville",
        "format": "paperback",
        "preferred_record_id": "BK-301",
        "merge_record_ids": "BK-300;BK-302",
        "all_record_ids": "BK-300;BK-301;BK-302",
        "member_count": 3,
        "branches_covered": 3,
        "total_copy_count": 4,
        "recent_loan_count": 6,
        "title_variant_count": 3,
        "confidence_reason": "same_normalized_isbn_and_format",
    }

    assert records["MERGE-002"] == {
        "candidate_id": "MERGE-002",
        "match_basis": "isbn",
        "normalized_isbn": "9780743273565",
        "normalized_title": "the great gatsby",
        "normalized_author": "f scott fitzgerald",
        "format": "hardcover",
        "preferred_record_id": "BK-100",
        "merge_record_ids": "BK-101",
        "all_record_ids": "BK-100;BK-101",
        "member_count": 2,
        "branches_covered": 2,
        "total_copy_count": 3,
        "recent_loan_count": 4,
        "title_variant_count": 2,
        "confidence_reason": "same_normalized_isbn_and_format",
    }

    assert records["MERGE-003"] == {
        "candidate_id": "MERGE-003",
        "match_basis": "title_author",
        "normalized_isbn": "",
        "normalized_title": "data science handbook",
        "normalized_author": "field cady",
        "format": "paperback",
        "preferred_record_id": "BK-200",
        "merge_record_ids": "BK-201",
        "all_record_ids": "BK-200;BK-201",
        "member_count": 2,
        "branches_covered": 2,
        "total_copy_count": 4,
        "recent_loan_count": 0,
        "title_variant_count": 2,
        "confidence_reason": "same_normalized_title_author_year_audience_format",
    }


def test_non_duplicate_records_are_excluded():
    output = pd.read_csv(OUTPUT_PATH, keep_default_na=False)
    all_ids = ";".join(output["all_record_ids"].tolist())

    for record_id in ["BK-102", "BK-202", "BK-400", "BK-500"]:
        assert record_id not in all_ids


def test_summary_metrics():
    with SUMMARY_PATH.open() as handle:
        summary = json.load(handle)

    assert summary == {
        "candidate_count": 3,
        "isbn_based_candidates": 2,
        "title_based_candidates": 1,
        "records_flagged_for_merge": 4,
        "preferred_records_with_zero_2025_loans": ["BK-200"],
        "max_candidate_size": 3,
        "total_recent_loan_count": 10,
    }
