import json
from pathlib import Path


OUTPUT = Path("/root/transfer2_service_coverage.json")
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
    assert OUTPUT.exists(), "missing service coverage output"


def test_payload_contract_and_values():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload["state"] == "California"
    assert payload["mission"] == "Mutual-aid lane coverage handoff"
    assert payload["tool_called"] == ["search_cities"]
    assert len(payload["selected_cities"]) == 4

    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}
    assert chosen == {
        "san_lane": "San Diego",
        "santa_lane": "Santa Rosa",
        "oak_lane": "Oakland",
        "southern_backup": "Long Beach",
    }
    assert payload["inspection_order"] == ["Oakland", "San Diego", "Long Beach", "Santa Rosa"]


def test_selection_is_consistent_with_lookup_rules():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    cities = load_mapping()["California"]
    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}

    assert chosen["san_lane"] == min((city for city in cities if city.startswith("San ")), key=lambda city: city)
    assert chosen["santa_lane"] == max((city for city in cities if city.startswith("Santa ")), key=lambda city: city)
    assert chosen["oak_lane"] == min(
        (city for city in cities if " " not in city and "k" in city.lower()),
        key=lambda city: (normalized_length(city), city),
    )
    assert chosen["southern_backup"] == min(
        (city for city in cities if " " in city and city.startswith("L")),
        key=lambda city: city,
    )
    assert payload["inspection_order"] == sorted(chosen.values(), key=lambda city: (normalized_length(city), city))
