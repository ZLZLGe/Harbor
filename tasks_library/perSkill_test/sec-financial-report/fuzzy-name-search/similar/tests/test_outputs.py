import json
from pathlib import Path


OUTPUT = Path("/root/fuzzy_lookup_answers.json")
EXPECTED = json.loads(Path("/tests/expected.json").read_text())


def test_output_exists():
    assert OUTPUT.exists(), "Missing /root/fuzzy_lookup_answers.json"


def test_answers_match():
    payload = json.loads(OUTPUT.read_text())
    assert payload == EXPECTED
