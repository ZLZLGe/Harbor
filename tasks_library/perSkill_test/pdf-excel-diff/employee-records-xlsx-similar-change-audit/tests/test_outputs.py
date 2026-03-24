#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path

OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", "/root/employee_workbook_diff.json"))

EXPECTED_OUTPUT = {
    "deleted_employee_ids": ["EMP00105", "EMP00109"],
    "modified_fields": [
        {
            "employee_id": "EMP00101",
            "field": "Salary",
            "old_value": 92000,
            "new_value": 96000,
        },
        {
            "employee_id": "EMP00102",
            "field": "Bonus %",
            "old_value": 0.05,
            "new_value": 0.055,
        },
        {
            "employee_id": "EMP00102",
            "field": "Department",
            "old_value": "Sales",
            "new_value": "Revenue",
        },
        {
            "employee_id": "EMP00103",
            "field": "Status",
            "old_value": "Leave",
            "new_value": "Active",
        },
        {
            "employee_id": "EMP00104",
            "field": "Location",
            "old_value": "Seattle",
            "new_value": "Portland",
        },
        {
            "employee_id": "EMP00106",
            "field": "Department",
            "old_value": "HR",
            "new_value": "People",
        },
        {
            "employee_id": "EMP00107",
            "field": "Bonus %",
            "old_value": 0.09,
            "new_value": 0.1,
        },
    ],
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    assert_true(OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}")

    with OUTPUT_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)

    assert_true(set(data.keys()) == {"deleted_employee_ids", "modified_fields"}, "Output keys do not match the expected schema")
    assert_true(data["deleted_employee_ids"] == EXPECTED_OUTPUT["deleted_employee_ids"], "Deleted employee IDs do not match")
    assert_true(data["modified_fields"] == EXPECTED_OUTPUT["modified_fields"], "Modified field entries do not match")

    assert_true(data["deleted_employee_ids"] == sorted(data["deleted_employee_ids"]), "Deleted employee IDs are not sorted")
    assert_true(
        data["modified_fields"] == sorted(data["modified_fields"], key=lambda item: (item["employee_id"], item["field"])),
        "Modified field entries are not sorted by employee_id then field",
    )

    for item in data["modified_fields"]:
        assert_true(set(item.keys()) == {"employee_id", "field", "old_value", "new_value"}, "A modified_fields entry has unexpected keys")
        if item["field"] in {"Salary", "Bonus %"}:
            assert_true(isinstance(item["old_value"], (int, float)), f"{item['employee_id']} {item['field']} old_value must be numeric")
            assert_true(isinstance(item["new_value"], (int, float)), f"{item['employee_id']} {item['field']} new_value must be numeric")
        else:
            assert_true(isinstance(item["old_value"], str), f"{item['employee_id']} {item['field']} old_value must be a string")
            assert_true(isinstance(item["new_value"], str), f"{item['employee_id']} {item['field']} new_value must be a string")


if __name__ == "__main__":
    main()
