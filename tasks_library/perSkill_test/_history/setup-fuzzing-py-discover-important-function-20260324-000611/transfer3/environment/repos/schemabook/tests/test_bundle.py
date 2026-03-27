from schemabook.bundle import load_schema_bundle, validate_schema_keys


def test_load_schema_bundle():
    bundle = load_schema_bundle('{"schemas": [{"name": "orders", "fields": ["id"]}]}')
    assert bundle["schemas"][0]["name"] == "orders"


def test_validate_schema_keys():
    missing = validate_schema_keys({"schemas": [{"name": "orders", "fields": ["id"]}, {"name": "audit"}]})
    assert missing == ["audit"]
