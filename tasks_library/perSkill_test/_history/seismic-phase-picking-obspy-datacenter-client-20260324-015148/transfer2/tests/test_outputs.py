import json
from pathlib import Path

EXPECTED = json.loads(Path("/tests/expected_event_digest.json").read_text(encoding="utf-8"))

def test_transfer2_json_matches_expected():
    output_path = Path("/root/transfer2_event_digest.json")
    assert output_path.exists(), "missing /root/transfer2_event_digest.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == EXPECTED
