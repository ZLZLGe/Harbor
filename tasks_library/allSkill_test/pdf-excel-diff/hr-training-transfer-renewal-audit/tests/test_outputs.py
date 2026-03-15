import json
from pathlib import Path


OUTPUT_FILE = Path("/root/training_compliance_discrepancies.json")
EXPECTED_FILE = Path("/tests/expected_output.json")


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


class TestOutputStructure:
    def test_output_file_exists(self):
        assert OUTPUT_FILE.exists(), f"Output file not found: {OUTPUT_FILE}"

    def test_output_is_valid_json(self):
        load_json(OUTPUT_FILE)

    def test_required_keys(self):
        data = load_json(OUTPUT_FILE)
        assert set(data) == {
            "dropped_employees",
            "status_regressions",
            "renewal_date_mismatches",
        }


class TestOutputContent:
    def test_exact_match(self):
        assert load_json(OUTPUT_FILE) == load_json(EXPECTED_FILE)

    def test_dropped_employees_sorted(self):
        data = load_json(OUTPUT_FILE)
        employee_ids = [item["employee_id"] for item in data["dropped_employees"]]
        assert employee_ids == sorted(employee_ids)

    def test_course_lists_sorted(self):
        data = load_json(OUTPUT_FILE)
        for key in ["status_regressions", "renewal_date_mismatches"]:
            pairs = [(item["employee_id"], item["course_code"]) for item in data[key]]
            assert pairs == sorted(pairs), f"{key} is not sorted by employee_id and course_code"

    def test_dropped_employee_shape(self):
        data = load_json(OUTPUT_FILE)
        for item in data["dropped_employees"]:
            assert set(item) == {"employee_id", "employee_name"}
            assert all(isinstance(item[key], str) for key in item)

    def test_status_regression_shape(self):
        data = load_json(OUTPUT_FILE)
        for item in data["status_regressions"]:
            assert set(item) == {
                "employee_id",
                "employee_name",
                "course_code",
                "archived_status",
                "current_status",
            }
            assert all(isinstance(item[key], str) for key in item)

    def test_renewal_mismatch_shape(self):
        data = load_json(OUTPUT_FILE)
        for item in data["renewal_date_mismatches"]:
            assert set(item) == {
                "employee_id",
                "employee_name",
                "course_code",
                "archived_renewal_date",
                "current_renewal_date",
            }
            assert all(isinstance(item[key], str) for key in item)

    def test_dropped_employees_excluded_from_other_lists(self):
        data = load_json(OUTPUT_FILE)
        dropped_ids = {item["employee_id"] for item in data["dropped_employees"]}
        regression_ids = {item["employee_id"] for item in data["status_regressions"]}
        mismatch_ids = {item["employee_id"] for item in data["renewal_date_mismatches"]}

        assert dropped_ids.isdisjoint(regression_ids)
        assert dropped_ids.isdisjoint(mismatch_ids)
