import json
from pathlib import Path

import pytest


OUTPUT_FILE = Path("/root/benefits_enrollment_diff.json")
EXPECTED_FILE = Path("/tests/expected_output.json")


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


class TestOutputStructure:
    def test_output_file_exists(self):
        assert OUTPUT_FILE.exists(), f"Output file not found: {OUTPUT_FILE}"

    def test_output_is_valid_json(self):
        assert OUTPUT_FILE.exists(), "Output file does not exist"
        load_json(OUTPUT_FILE)

    def test_required_keys_present(self):
        data = load_json(OUTPUT_FILE)
        assert set(data) == {
            "removed_employees",
            "tier_changes",
            "dependent_count_changes",
            "salary_band_changes",
        }


class TestOutputContent:
    def test_exact_match(self):
        assert load_json(OUTPUT_FILE) == load_json(EXPECTED_FILE)

    def test_removed_employees_sorted(self):
        output = load_json(OUTPUT_FILE)
        assert output["removed_employees"] == sorted(output["removed_employees"])

    @pytest.mark.parametrize(
        ("list_key", "id_key"),
        [
            ("tier_changes", "employee_id"),
            ("dependent_count_changes", "employee_id"),
            ("salary_band_changes", "employee_id"),
        ],
    )
    def test_change_lists_sorted(self, list_key, id_key):
        output = load_json(OUTPUT_FILE)
        employee_ids = [item[id_key] for item in output[list_key]]
        assert employee_ids == sorted(employee_ids)

    def test_numeric_fields_are_numbers(self):
        output = load_json(OUTPUT_FILE)
        for item in output["dependent_count_changes"]:
            assert isinstance(item["old_dependents"], int)
            assert isinstance(item["new_dependents"], int)

    def test_text_fields_are_strings(self):
        output = load_json(OUTPUT_FILE)
        for item in output["tier_changes"]:
            assert isinstance(item["old_tier"], str)
            assert isinstance(item["new_tier"], str)
        for item in output["salary_band_changes"]:
            assert isinstance(item["old_salary_band"], str)
            assert isinstance(item["new_salary_band"], str)
