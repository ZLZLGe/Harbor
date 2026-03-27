import json
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer3_handoff_notes.json")
EXPECTED_PATH = Path("/tests/expected.json")


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_matches_expected():
    generated = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    assert generated == expected
