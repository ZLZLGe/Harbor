import json
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer1_badge_denials.json")

EXPECTED = {
    "site": "north-plant",
    "denied_count": 3,
    "doors": [
        {"door": "A1", "count": 2},
        {"door": "A2", "count": 1},
    ],
    "badges": ["B-104", "B-210"],
    "events": [
        {"frame_number": 4, "door": "A1", "badge": "B-104", "reason": "expired"},
        {"frame_number": 16, "door": "A2", "badge": "B-210", "reason": "tailgating"},
        {"frame_number": 28, "door": "A1", "badge": "B-104", "reason": "expired"},
    ],
}


def test_expected_json():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    actual = json.loads(OUTPUT_PATH.read_text())
    assert actual == EXPECTED


def main() -> None:
    test_expected_json()
    print("transfer1 verifier checks passed")


if __name__ == "__main__":
    main()
