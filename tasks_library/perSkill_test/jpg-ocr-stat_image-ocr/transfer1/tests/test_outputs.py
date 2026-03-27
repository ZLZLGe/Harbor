import json
import os


def test_outputs() -> None:
    actual_path = "/app/workspace/transfer1_monthly_summary.json"
    expected_path = os.path.join(os.path.dirname(__file__), "transfer1_oracle.json")

    assert os.path.exists(actual_path), "Output file missing: /app/workspace/transfer1_monthly_summary.json"

    with open(actual_path, "r", encoding="utf-8") as f:
        actual = json.load(f)
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    assert actual == expected, f"JSON mismatch.\nActual: {actual}\nExpected: {expected}"
