import json
from pathlib import Path


OUTPUT = Path("/root/issuer_resolution.json")
EXPECTED = json.loads(Path("/tests/expected.json").read_text())


def test_output_exists():
    assert OUTPUT.exists(), "Missing /root/issuer_resolution.json"


def test_resolution_matches_expected():
    payload = json.loads(OUTPUT.read_text())
    assert payload == EXPECTED
