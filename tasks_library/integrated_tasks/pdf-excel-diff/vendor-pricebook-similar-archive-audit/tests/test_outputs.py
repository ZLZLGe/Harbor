import json
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/vendor_catalog_diff.json")
EXPECTED_FILE = Path("/tests/expected_output.json")


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def assert_numeric_match(left, right):
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        assert abs(left - right) < 1e-9
    else:
        assert left == right


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_is_valid_json():
    load_json(OUTPUT_FILE)


def test_required_structure():
    data = load_json(OUTPUT_FILE)
    assert set(data.keys()) == {"discontinued_skus", "modified_skus"}
    assert isinstance(data["discontinued_skus"], list)
    assert isinstance(data["modified_skus"], list)


def test_sorted_order():
    data = load_json(OUTPUT_FILE)
    assert data["discontinued_skus"] == sorted(data["discontinued_skus"])
    assert data["modified_skus"] == sorted(
        data["modified_skus"],
        key=lambda item: (item["sku"], item["field"]),
    )


def test_exact_discontinued_skus():
    output = load_json(OUTPUT_FILE)
    expected = load_json(EXPECTED_FILE)
    assert output["discontinued_skus"] == expected["discontinued_skus"]


def test_modified_entries_match_expected():
    output = load_json(OUTPUT_FILE)
    expected = load_json(EXPECTED_FILE)

    assert len(output["modified_skus"]) == len(expected["modified_skus"])

    for actual, wanted in zip(output["modified_skus"], expected["modified_skus"]):
        assert actual["sku"] == wanted["sku"]
        assert actual["field"] == wanted["field"]
        assert_numeric_match(actual["old_value"], wanted["old_value"])
        assert_numeric_match(actual["new_value"], wanted["new_value"])


@pytest.mark.parametrize("field", ["UnitPrice", "PackSize", "LeadTimeDays"])
def test_numeric_fields_remain_numeric(field):
    output = load_json(OUTPUT_FILE)
    for item in output["modified_skus"]:
        if item["field"] == field:
            assert isinstance(item["old_value"], (int, float))
            assert isinstance(item["new_value"], (int, float))
