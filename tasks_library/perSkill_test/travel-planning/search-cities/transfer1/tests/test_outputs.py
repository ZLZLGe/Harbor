import json
from pathlib import Path


OUTPUT = Path("/root/transfer1_training_hubs.json")
DATA = Path("/root/data/background/citySet_with_states.txt")


def normalized_length(city: str) -> int:
    return len(city.replace(" ", ""))


def load_mapping():
    mapping = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        city, state = line.split("\t")
        mapping.setdefault(state.strip(), []).append(city.strip())
    return mapping


def test_output_exists():
    assert OUTPUT.exists(), "missing training hubs output"


def test_payload_contract_and_values():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload["state"] == "Texas"
    assert payload["program"] == "Field mentor roadshow"
    assert payload["tool_called"] == ["search_cities"]
    assert len(payload["selected_cities"]) == 4

    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}
    assert chosen == {
        "campus_anchor": "College Station",
        "drive_through_stop": "Waco",
        "coastal_gateway": "Beaumont",
        "backup_single_word": "Brownsville",
    }
    assert payload["rotation_order"] == ["Waco", "Beaumont", "Brownsville", "College Station"]


def test_selection_is_consistent_with_lookup_rules():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    cities = load_mapping()["Texas"]
    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}

    two_word = [city for city in cities if " " in city]
    max_two_word = max(normalized_length(city) for city in two_word)
    expected_anchor = min((city for city in two_word if normalized_length(city) == max_two_word), key=lambda city: city)
    expected_drive = min((city for city in cities if city.lower().endswith("o")), key=lambda city: (normalized_length(city), city))
    expected_gateway = min((city for city in cities if city.startswith("B")), key=lambda city: city)
    blocked = {expected_anchor, expected_drive, expected_gateway}
    expected_backup = max(
        (city for city in cities if " " not in city and city not in blocked),
        key=lambda city: (normalized_length(city), city),
    )

    assert chosen["campus_anchor"] == expected_anchor
    assert chosen["drive_through_stop"] == expected_drive
    assert chosen["coastal_gateway"] == expected_gateway
    assert chosen["backup_single_word"] == expected_backup
    assert payload["rotation_order"] == sorted(chosen.values(), key=lambda city: (normalized_length(city), city))
