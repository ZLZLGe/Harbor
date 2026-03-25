import json
from pathlib import Path


OUTPUT = Path("/root/transfer3_outreach_schedule.json")
DATA = Path("/root/data/background/citySet_with_states.txt")


def normalized_length(city: str) -> int:
    return len(city.replace(" ", ""))


def word_count(city: str) -> int:
    return len(city.split())


def load_mapping():
    mapping = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        city, state = line.split("\t")
        mapping.setdefault(state.strip(), []).append(city.strip())
    return mapping


def test_output_exists():
    assert OUTPUT.exists(), "missing outreach schedule output"


def test_payload_contract_and_values():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload["state"] == "Florida"
    assert payload["program"] == "Mobile services outreach schedule"
    assert payload["tool_called"] == ["search_cities"]
    assert len(payload["selected_cities"]) == 4

    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}
    assert chosen == {
        "clinic_anchor": "Jacksonville",
        "weekend_stop": "Key West",
        "permit_city": "Panama City",
        "comms_backup": "Fort Lauderdale",
    }
    assert payload["visit_sequence"] == ["Fort Lauderdale", "Key West", "Panama City", "Jacksonville"]


def test_selection_is_consistent_with_lookup_rules():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    cities = load_mapping()["Florida"]
    chosen = {item["slot"]: item["city"] for item in payload["selected_cities"]}

    assert chosen["clinic_anchor"] == max(
        (city for city in cities if " " not in city),
        key=lambda city: (normalized_length(city), city),
    )
    assert chosen["weekend_stop"] == min(
        (city for city in cities if " " in city),
        key=lambda city: (normalized_length(city), city),
    )
    assert chosen["permit_city"] == min((city for city in cities if "City" in city.split()), key=lambda city: city)
    assert chosen["comms_backup"] == max(
        (city for city in cities if " " in city),
        key=lambda city: (normalized_length(city), city),
    )
    assert payload["visit_sequence"] == sorted(chosen.values(), key=lambda city: (-word_count(city), city))
