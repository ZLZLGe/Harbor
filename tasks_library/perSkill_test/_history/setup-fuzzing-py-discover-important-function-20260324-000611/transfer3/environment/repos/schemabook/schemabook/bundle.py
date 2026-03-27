import json


def load_schema_bundle(raw: str) -> dict[str, object]:
    """Load a JSON bundle of schema documents."""
    return json.loads(raw)


def validate_schema_keys(bundle: dict[str, object]) -> list[str]:
    """Report schema entries that miss a required `fields` key."""
    missing = []
    for entry in bundle.get("schemas", []):
        if "fields" not in entry:
            missing.append(entry["name"])
    return missing


def schema_names(bundle: dict[str, object]) -> list[str]:
    return [entry["name"] for entry in bundle.get("schemas", [])]
