import json
from pathlib import Path


output = Path("/root/aurora_rotation_summary.json")
expected = json.loads(Path("/tests/expected.json").read_text())

assert output.exists(), "Missing /root/aurora_rotation_summary.json"
payload = json.loads(output.read_text())
assert payload == expected
