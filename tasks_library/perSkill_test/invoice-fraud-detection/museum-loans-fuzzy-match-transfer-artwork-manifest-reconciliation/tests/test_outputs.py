import json
import os


EXPECTED_ROWS = [
    {
        "manifest_line_id": "ML-003",
        "crate_id": "CR-02",
        "shipped_artwork_title": "Still Life with Copper Ketle",
        "matched_catalog_id": "ART-403",
        "matched_catalog_title": "Still Life with Copper Kettle",
        "borrowing_institution": "Gallery of Northern Trades",
        "insurance_policy_number": "POL-GNT-0000",
        "reason": "Insurance Policy Mismatch",
    },
    {
        "manifest_line_id": "ML-004",
        "crate_id": "CR-02",
        "shipped_artwork_title": "Harbor Ledger 1921",
        "matched_catalog_id": "ART-404",
        "matched_catalog_title": "Harbor Ledger, 1921",
        "borrowing_institution": "Port City Maritime Museum",
        "insurance_policy_number": "POL-PCH-6612",
        "reason": "Borrowing Institution Mismatch",
    },
    {
        "manifest_line_id": "ML-005",
        "crate_id": "CR-03",
        "shipped_artwork_title": "Garden Variations",
        "matched_catalog_id": None,
        "matched_catalog_title": None,
        "borrowing_institution": "Midland Sculpture Hall",
        "insurance_policy_number": "POL-MSH-5520",
        "reason": "Unmatched Artwork",
    },
    {
        "manifest_line_id": "ML-008",
        "crate_id": "CR-04",
        "shipped_artwork_title": "Signal House - East Facade",
        "matched_catalog_id": "ART-409",
        "matched_catalog_title": "Signal House: East Facade",
        "borrowing_institution": "Metropolitan Architecture Archive",
        "insurance_policy_number": "POL-MAA-0000",
        "reason": "Insurance Policy Mismatch",
    },
    {
        "manifest_line_id": "ML-009",
        "crate_id": "CR-05",
        "shipped_artwork_title": "Sea Clock in Amber",
        "matched_catalog_id": "ART-410",
        "matched_catalog_title": "Sea Clock in Amber",
        "borrowing_institution": "Royal Marine Gallery",
        "insurance_policy_number": "POL-RMG-0000",
        "reason": "Borrowing Institution Mismatch",
    },
    {
        "manifest_line_id": "ML-010",
        "crate_id": "CR-05",
        "shipped_artwork_title": "Portrait of the Bronze Archivist",
        "matched_catalog_id": None,
        "matched_catalog_title": None,
        "borrowing_institution": "Museum of Coastal Light",
        "insurance_policy_number": "POL-CL-9999",
        "reason": "Unmatched Artwork",
    },
]


def load_output():
    with open("/root/loan_manifest_flags.ndjson", encoding="utf-8") as handle:
        raw = handle.read()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return raw, rows


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/loan_manifest_flags.ndjson")

    def test_ndjson_not_array(self):
        raw, rows = load_output()
        assert raw.strip()
        assert not raw.lstrip().startswith("[")
        assert len(rows) == len(EXPECTED_ROWS)

    def test_exact_flagged_rows(self):
        _, rows = load_output()
        assert rows == EXPECTED_ROWS

    def test_clean_manifest_lines_not_flagged(self):
        _, rows = load_output()
        flagged_ids = {row["manifest_line_id"] for row in rows}
        clean_ids = {"ML-001", "ML-002", "ML-006", "ML-007"}
        assert flagged_ids.isdisjoint(clean_ids)

    def test_unmatched_rows_have_null_match_fields(self):
        _, rows = load_output()
        unmatched = [row for row in rows if row["reason"] == "Unmatched Artwork"]
        assert unmatched == [
            {
                "manifest_line_id": "ML-005",
                "crate_id": "CR-03",
                "shipped_artwork_title": "Garden Variations",
                "matched_catalog_id": None,
                "matched_catalog_title": None,
                "borrowing_institution": "Midland Sculpture Hall",
                "insurance_policy_number": "POL-MSH-5520",
                "reason": "Unmatched Artwork",
            },
            {
                "manifest_line_id": "ML-010",
                "crate_id": "CR-05",
                "shipped_artwork_title": "Portrait of the Bronze Archivist",
                "matched_catalog_id": None,
                "matched_catalog_title": None,
                "borrowing_institution": "Museum of Coastal Light",
                "insurance_policy_number": "POL-CL-9999",
                "reason": "Unmatched Artwork",
            },
        ]

    def test_reason_precedence_keeps_institution_before_policy(self):
        _, rows = load_output()
        sea_clock = next(row for row in rows if row["manifest_line_id"] == "ML-009")
        assert sea_clock["reason"] == "Borrowing Institution Mismatch"
