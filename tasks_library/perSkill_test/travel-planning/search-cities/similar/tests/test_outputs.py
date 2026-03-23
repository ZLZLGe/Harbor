import json
from pathlib import Path


OUTPUT = Path("/root/similar_trip_city_shortlist.json")
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
    assert OUTPUT.exists(), "missing shortlist output"


def test_payload_contract_and_values():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload["state"] == "Ohio"
    assert payload["trip_days"] == 7
    assert payload["tool_called"] == ["search_cities"]
    assert len(payload["selected_cities"]) == 3

    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}
    assert chosen == {
        "anchor_city": "Cincinnati",
        "connector_city": "Columbus",
        "buffer_city": "Toledo",
    }
    assert payload["route_order"] == ["Toledo", "Columbus", "Cincinnati"]


def test_selection_is_consistent_with_lookup_rules():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    cities = load_mapping()["Ohio"]
    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}

    assert chosen["anchor_city"] == min((city for city in cities if city.startswith("C")), key=lambda city: city)
    assert chosen["connector_city"] == max(
        (city for city in cities if "o" in city.lower()),
        key=lambda city: (normalized_length(city), city),
    )
    assert chosen["buffer_city"] == max(
        (city for city in cities if normalized_length(city) == 6),
        key=lambda city: city,
    )
    assert payload["route_order"] == sorted(chosen.values(), key=lambda city: (normalized_length(city), city))
