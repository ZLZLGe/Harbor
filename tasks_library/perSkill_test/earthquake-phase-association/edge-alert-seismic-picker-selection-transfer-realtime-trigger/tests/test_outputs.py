import json
import os
from pathlib import Path


OUTPUT_FILE = Path(os.environ.get("EDGE_OUTPUT_FILE", "/root/edge_trigger_strategy.json"))

EXPECTED_STA_NAMES = {
    "sta_window_seconds",
    "lta_window_seconds",
    "trigger_ratio",
    "detrigger_ratio",
    "cooldown_seconds",
}


def load_output():
    with OUTPUT_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def to_parameter_map(parameter_list):
    return {entry["name"]: entry["value"] for entry in parameter_list}


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_schema_and_method_choice():
    payload = load_output()
    assert set(payload.keys()) == {"method_name", "key_parameters", "reason"}
    assert payload["method_name"] == "sta_lta"
    assert isinstance(payload["key_parameters"], list)
    assert isinstance(payload["reason"], str)


def test_sta_lta_parameter_names_and_types():
    payload = load_output()
    parameters = payload["key_parameters"]
    assert len(parameters) == 5

    for entry in parameters:
        assert set(entry.keys()) == {"name", "value"}
        assert isinstance(entry["name"], str)
        assert isinstance(entry["value"], (int, float))

    parameter_map = to_parameter_map(parameters)
    assert set(parameter_map.keys()) == EXPECTED_STA_NAMES


def test_sta_lta_parameters_fit_instruction_ranges():
    payload = load_output()
    params = to_parameter_map(payload["key_parameters"])

    assert 0.3 <= params["sta_window_seconds"] <= 1.2
    assert 4.0 <= params["lta_window_seconds"] <= 12.0
    assert 2.5 <= params["trigger_ratio"] <= 4.5
    assert 1.1 <= params["detrigger_ratio"] <= 2.0
    assert 1.0 <= params["cooldown_seconds"] <= 6.0

    assert params["lta_window_seconds"] > 4 * params["sta_window_seconds"]
    assert params["trigger_ratio"] > params["detrigger_ratio"]


def test_reason_is_short_plain_text():
    payload = load_output()
    reason = payload["reason"].strip()
    assert "\n" not in reason
