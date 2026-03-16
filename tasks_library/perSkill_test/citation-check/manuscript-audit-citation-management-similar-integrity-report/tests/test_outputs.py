import json
from pathlib import Path

import pytest

ANSWER_FILE = Path("/root/bibliography_audit.json")
EXPECTED_KEYS = [
    "brown2021quantum",
    "chen2024agents",
    "lee2023federated",
    "miller2022survey",
]
EXPECTED_ISSUES = {
    "brown2021quantum": ["metadata_mismatch"],
    "chen2024agents": ["invalid_doi", "missing_required_fields"],
    "lee2023federated": ["invalid_doi"],
    "miller2022survey": ["missing_required_fields"],
}
EXPECTED_MISSING_FIELDS = {
    "brown2021quantum": [],
    "chen2024agents": ["booktitle"],
    "lee2023federated": [],
    "miller2022survey": ["journal"],
}


def load_answer() -> dict:
    assert ANSWER_FILE.exists(), f"Answer file not found at {ANSWER_FILE}"
    with ANSWER_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


class TestAnswerStructure:
    def test_file_exists(self):
        assert ANSWER_FILE.exists(), f"Answer file not found at {ANSWER_FILE}"

    def test_valid_json(self):
        with ANSWER_FILE.open(encoding="utf-8") as handle:
            try:
                json.load(handle)
            except json.JSONDecodeError as exc:
                pytest.fail(f"Answer file is not valid JSON: {exc}")

    def test_top_level_keys(self):
        data = load_answer()
        assert set(data.keys()) == {
            "audited_file",
            "total_entries",
            "flagged_entry_count",
            "flagged_entries",
        }

    def test_summary_values(self):
        data = load_answer()
        assert data["audited_file"] == "/root/manuscript_refs.bib"
        assert data["total_entries"] == 7
        assert data["flagged_entry_count"] == 4
        assert isinstance(data["flagged_entries"], list)
        assert len(data["flagged_entries"]) == data["flagged_entry_count"]


class TestFlaggedEntries:
    def test_keys_sorted_and_exact(self):
        data = load_answer()
        actual_keys = [item["citation_key"] for item in data["flagged_entries"]]
        assert actual_keys == EXPECTED_KEYS

    def test_each_entry_has_required_fields(self):
        data = load_answer()
        for item in data["flagged_entries"]:
            assert set(item.keys()) == {
                "citation_key",
                "title",
                "issue_types",
                "missing_fields",
                "notes",
            }
            assert isinstance(item["citation_key"], str) and item["citation_key"]
            assert isinstance(item["title"], str) and item["title"]
            assert isinstance(item["issue_types"], list)
            assert isinstance(item["missing_fields"], list)
            assert isinstance(item["notes"], list) and item["notes"]

    def test_expected_issue_types(self):
        data = load_answer()
        for item in data["flagged_entries"]:
            expected = EXPECTED_ISSUES[item["citation_key"]]
            assert item["issue_types"] == expected

    def test_expected_missing_fields(self):
        data = load_answer()
        for item in data["flagged_entries"]:
            expected = EXPECTED_MISSING_FIELDS[item["citation_key"]]
            assert item["missing_fields"] == expected

    def test_titles_are_cleaned(self):
        data = load_answer()
        for item in data["flagged_entries"]:
            assert "{" not in item["title"]
            assert "}" not in item["title"]
            assert "\\" not in item["title"]

    def test_notes_include_doi_context_when_needed(self):
        data = load_answer()
        for item in data["flagged_entries"]:
            note_blob = " ".join(item["notes"])
            if "invalid_doi" in item["issue_types"] or "metadata_mismatch" in item["issue_types"]:
                assert "10." in note_blob

    def test_only_allowed_issue_labels(self):
        data = load_answer()
        allowed = {"invalid_doi", "metadata_mismatch", "missing_required_fields"}
        for item in data["flagged_entries"]:
            assert set(item["issue_types"]).issubset(allowed)
            assert item["issue_types"] == sorted(set(item["issue_types"]))
