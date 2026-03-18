import json
import re
from pathlib import Path

OUTPUT_FILE = Path("/root/equipment_registry_changes.json")
EXPECTED_FILE = Path("/tests/expected_output.json")


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"


def test_output_is_valid_json():
    load_json(OUTPUT_FILE)


def test_required_structure():
    data = load_json(OUTPUT_FILE)
    assert set(data.keys()) == {"retired_equipment", "updated_records"}
    assert isinstance(data["retired_equipment"], list)
    assert isinstance(data["updated_records"], list)


def test_sorted_order():
    data = load_json(OUTPUT_FILE)
    assert data["retired_equipment"] == sorted(data["retired_equipment"])
    assert data["updated_records"] == sorted(
        data["updated_records"],
        key=lambda item: (item["asset_tag"], item["field"]),
    )


def test_exact_output_matches_expected():
    assert load_json(OUTPUT_FILE) == load_json(EXPECTED_FILE)


def test_date_values_are_normalized():
    iso_date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    output = load_json(OUTPUT_FILE)
    for item in output["updated_records"]:
        if item["field"] == "next_inspection_date":
            assert isinstance(item["old_value"], str)
            assert isinstance(item["new_value"], str)
            assert iso_date.match(item["old_value"])
            assert iso_date.match(item["new_value"])


def test_interval_values_are_integers():
    output = load_json(OUTPUT_FILE)
    for item in output["updated_records"]:
        if item["field"] == "inspection_interval_days":
            assert isinstance(item["old_value"], int)
            assert isinstance(item["new_value"], int)


def test_text_fields_remain_strings():
    output = load_json(OUTPUT_FILE)
    for item in output["updated_records"]:
        if item["field"] in {"service_vendor", "risk_level"}:
            assert isinstance(item["old_value"], str)
            assert isinstance(item["new_value"], str)
