import json
from pathlib import Path


OUTPUT_FILE = Path("/root/badge_clearance_audit.json")
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
            "removed_badges",
            "zone_changes",
            "clearance_policy_violations",
        }


class TestOutputContent:
    def test_exact_match(self):
        assert load_json(OUTPUT_FILE) == load_json(EXPECTED_FILE)

    def test_all_lists_are_sorted(self):
        data = load_json(OUTPUT_FILE)
        for key in data:
            employee_ids = [item["employee_id"] for item in data[key]]
            assert employee_ids == sorted(employee_ids), f"{key} is not sorted by employee_id"

    def test_removed_badges_shape(self):
        data = load_json(OUTPUT_FILE)
        for item in data["removed_badges"]:
            assert set(item) == {"employee_id", "badge_id"}
            assert isinstance(item["employee_id"], str)
            assert isinstance(item["badge_id"], str)

    def test_zone_changes_shape(self):
        data = load_json(OUTPUT_FILE)
        for item in data["zone_changes"]:
            assert set(item) == {"employee_id", "badge_id", "old_zone", "new_zone"}
            assert all(isinstance(item[key], str) for key in item)

    def test_clearance_violations_shape(self):
        data = load_json(OUTPUT_FILE)
        for item in data["clearance_policy_violations"]:
            assert set(item) == {
                "employee_id",
                "badge_id",
                "zone",
                "required_clearance",
                "actual_clearance",
            }
            assert all(isinstance(item[key], str) for key in item)

    def test_removed_badges_not_repeated_elsewhere(self):
        data = load_json(OUTPUT_FILE)
        removed_ids = {item["employee_id"] for item in data["removed_badges"]}
        zone_ids = {item["employee_id"] for item in data["zone_changes"]}
        violation_ids = {item["employee_id"] for item in data["clearance_policy_violations"]}

        assert removed_ids.isdisjoint(zone_ids)
        assert removed_ids.isdisjoint(violation_ids)
