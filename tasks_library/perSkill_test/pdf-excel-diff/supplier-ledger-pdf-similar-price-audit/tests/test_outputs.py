import json
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/supplier_price_diff.json")
EXPECTED = {
    "discontinued_skus": [
        "SUP-1007",
        "SUP-1018",
        "SUP-1029",
        "SUP-1037",
    ],
    "updated_products": [
        {"sku": "SUP-1003", "field": "UnitPrice", "old_value": 4.85, "new_value": 5.10},
        {"sku": "SUP-1009", "field": "LeadDays", "old_value": 12, "new_value": 15},
        {"sku": "SUP-1009", "field": "MOQ", "old_value": 500, "new_value": 600},
        {
            "sku": "SUP-1012",
            "field": "Description",
            "old_value": "Vinyl Glove L",
            "new_value": "Vinyl Glove Large",
        },
        {"sku": "SUP-1015", "field": "UnitPrice", "old_value": 18.75, "new_value": 17.95},
        {
            "sku": "SUP-1021",
            "field": "Category",
            "old_value": "Adhesive",
            "new_value": "Sealants",
        },
        {"sku": "SUP-1024", "field": "LeadDays", "old_value": 20, "new_value": 18},
        {"sku": "SUP-1024", "field": "UnitPrice", "old_value": 42.0, "new_value": 39.5},
        {"sku": "SUP-1034", "field": "MOQ", "old_value": 25, "new_value": 30},
        {"sku": "SUP-1039", "field": "UnitPrice", "old_value": 8.6, "new_value": 8.95},
    ],
}
NUMERIC_FIELDS = {"UnitPrice", "LeadDays", "MOQ"}


def load_output():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    with OUTPUT_FILE.open() as handle:
        return json.load(handle)


def normalize_entry(entry):
    normalized = dict(entry)
    if normalized["field"] in NUMERIC_FIELDS:
        normalized["old_value"] = float(normalized["old_value"])
        normalized["new_value"] = float(normalized["new_value"])
    return normalized


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"


def test_output_is_valid_json():
    with OUTPUT_FILE.open() as handle:
        try:
            json.load(handle)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Output file is not valid JSON: {exc}")


def test_top_level_shape():
    data = load_output()
    assert set(data.keys()) == {"discontinued_skus", "updated_products"}
    assert isinstance(data["discontinued_skus"], list)
    assert isinstance(data["updated_products"], list)


def test_discontinued_skus_exact_and_sorted():
    data = load_output()
    assert data["discontinued_skus"] == EXPECTED["discontinued_skus"]


def test_updated_products_exact_and_sorted():
    data = load_output()
    normalized_output = [normalize_entry(entry) for entry in data["updated_products"]]
    normalized_expected = [normalize_entry(entry) for entry in EXPECTED["updated_products"]]
    assert normalized_output == normalized_expected


def test_updated_product_entry_shape():
    data = load_output()
    for entry in data["updated_products"]:
        assert set(entry.keys()) == {"sku", "field", "old_value", "new_value"}


def test_numeric_fields_use_numeric_values():
    data = load_output()
    for entry in data["updated_products"]:
        if entry["field"] in NUMERIC_FIELDS:
            assert isinstance(entry["old_value"], (int, float))
            assert isinstance(entry["new_value"], (int, float))
        else:
            assert isinstance(entry["old_value"], str)
            assert isinstance(entry["new_value"], str)
