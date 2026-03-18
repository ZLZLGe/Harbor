import json
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/shipping_manifest_variances.json")
EXPECTED_FILE = Path("/tests/expected_output.json")

INT_FIELDS = {"line_no", "carton_count"}
FLOAT_FIELDS = {"gross_weight_kg", "declared_value_usd"}


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def assert_value_match(actual, expected):
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        assert abs(actual - expected) < 1e-9
    else:
        assert actual == expected


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_is_valid_json():
    load_json(OUTPUT_FILE)


def test_required_structure():
    data = load_json(OUTPUT_FILE)
    assert set(data.keys()) == {"missing_line_items", "changed_line_items"}
    assert isinstance(data["missing_line_items"], list)
    assert isinstance(data["changed_line_items"], list)


def test_sorted_order():
    data = load_json(OUTPUT_FILE)
    assert data["missing_line_items"] == sorted(
        data["missing_line_items"],
        key=lambda item: (item["manifest_id"], item["line_no"]),
    )
    assert data["changed_line_items"] == sorted(
        data["changed_line_items"],
        key=lambda item: (item["manifest_id"], item["line_no"], item["field"]),
    )


def test_missing_line_items_exact_match():
    output = load_json(OUTPUT_FILE)
    expected = load_json(EXPECTED_FILE)
    assert output["missing_line_items"] == expected["missing_line_items"]


def test_changed_line_items_exact_match():
    output = load_json(OUTPUT_FILE)
    expected = load_json(EXPECTED_FILE)

    assert len(output["changed_line_items"]) == len(expected["changed_line_items"])

    for actual, wanted in zip(output["changed_line_items"], expected["changed_line_items"]):
        assert actual["manifest_id"] == wanted["manifest_id"]
        assert actual["line_no"] == wanted["line_no"]
        assert actual["field"] == wanted["field"]
        assert_value_match(actual["old_value"], wanted["old_value"])
        assert_value_match(actual["new_value"], wanted["new_value"])


@pytest.mark.parametrize("field", ["destination_port"])
def test_text_fields_are_strings(field):
    output = load_json(OUTPUT_FILE)
    for item in output["changed_line_items"]:
        if item["field"] == field:
            assert isinstance(item["old_value"], str)
            assert isinstance(item["new_value"], str)


@pytest.mark.parametrize("field", ["carton_count"])
def test_integer_fields_are_ints(field):
    output = load_json(OUTPUT_FILE)
    for item in output["changed_line_items"]:
        if item["field"] == field:
            assert isinstance(item["old_value"], int)
            assert isinstance(item["new_value"], int)


@pytest.mark.parametrize("field", ["gross_weight_kg", "declared_value_usd"])
def test_float_fields_are_numeric(field):
    output = load_json(OUTPUT_FILE)
    for item in output["changed_line_items"]:
        if item["field"] == field:
            assert isinstance(item["old_value"], (int, float))
            assert isinstance(item["new_value"], (int, float))


def test_missing_rows_do_not_appear_in_changes():
    output = load_json(OUTPUT_FILE)
    missing_keys = {
        (item["manifest_id"], item["line_no"])
        for item in output["missing_line_items"]
    }
    changed_keys = {
        (item["manifest_id"], item["line_no"])
        for item in output["changed_line_items"]
    }
    assert missing_keys.isdisjoint(changed_keys)
