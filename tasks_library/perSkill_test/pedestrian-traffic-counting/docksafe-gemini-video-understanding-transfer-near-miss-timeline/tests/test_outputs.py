import json
import os
import re


OUTPUT_FILE = "/app/loading_dock/near_miss_timeline.json"
REWARD_FILE = "/logs/verifier/reward.txt"
ALLOWED_OBJECTS = {"forklift", "pedestrian", "handcart"}
EXPECTED_EVENTS = [
    {
        "video": "bay_alpha.avi",
        "timestamp": "00:06",
        "objects": ["forklift", "pedestrian"],
        "keywords": ["walkway", "gap", "close", "clearance"],
    },
    {
        "video": "bay_alpha.avi",
        "timestamp": "00:15",
        "objects": ["forklift", "handcart"],
        "keywords": ["handcart", "cart", "fork", "clearance", "gap"],
    },
    {
        "video": "bay_bravo.avi",
        "timestamp": "00:08",
        "objects": ["forklift", "pedestrian"],
        "keywords": ["walkway", "yield", "gap", "close", "pedestrian"],
    },
    {
        "video": "bay_bravo.avi",
        "timestamp": "00:19",
        "objects": ["forklift", "handcart"],
        "keywords": ["handcart", "cart", "corner", "gap", "clearance"],
    },
]


def _write_reward(value: float) -> None:
    os.makedirs(os.path.dirname(REWARD_FILE), exist_ok=True)
    with open(REWARD_FILE, "w", encoding="utf-8") as handle:
        handle.write(f"{value:.6f}\n")


def _load_output() -> list[dict]:
    with open(OUTPUT_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, list), "Output must be a JSON array"
    return data


def _validate_record(record: dict, index: int) -> None:
    assert isinstance(record, dict), f"Record {index} must be a JSON object"
    assert set(record) == {"video", "timestamp", "objects", "evidence"}, (
        f"Record {index} must contain exactly video, timestamp, objects, evidence; got {sorted(record)}"
    )
    assert isinstance(record["video"], str) and record["video"], f"Record {index} video must be a non-empty string"
    assert re.fullmatch(r"\d{2}:\d{2}", record["timestamp"]), (
        f"Record {index} timestamp must use MM:SS, got {record['timestamp']!r}"
    )
    assert isinstance(record["objects"], list), f"Record {index} objects must be a list"
    assert len(record["objects"]) == 2, f"Record {index} must list exactly two objects"
    assert record["objects"] == sorted(record["objects"]), f"Record {index} objects must be sorted alphabetically"
    assert len(set(record["objects"])) == 2, f"Record {index} objects must not repeat"
    assert set(record["objects"]).issubset(ALLOWED_OBJECTS), (
        f"Record {index} objects must come from {sorted(ALLOWED_OBJECTS)}, got {record['objects']}"
    )
    assert isinstance(record["evidence"], str), f"Record {index} evidence must be a string"
    evidence = record["evidence"].strip()
    assert evidence, f"Record {index} evidence must not be empty"
    assert len(evidence) <= 180, f"Record {index} evidence is too long"


def test_outputs() -> None:
    if not os.path.exists(OUTPUT_FILE):
        _write_reward(0.0)
        raise AssertionError("near_miss_timeline.json not found at /app/loading_dock")

    try:
        data = _load_output()
        assert len(data) == len(EXPECTED_EVENTS), (
            f"Expected {len(EXPECTED_EVENTS)} near-miss records, got {len(data)}"
        )

        for idx, record in enumerate(data):
            _validate_record(record, idx)

        actual_order = [(item["video"], item["timestamp"]) for item in data]
        assert actual_order == sorted(actual_order), "Records must be sorted by video then timestamp"
        assert len(set(actual_order)) == len(actual_order), "Duplicate video/timestamp records are not allowed"

        actual_map = {(item["video"], item["timestamp"]): item for item in data}

        total_reward = 0.0
        for expected in EXPECTED_EVENTS:
            key = (expected["video"], expected["timestamp"])
            record = actual_map.get(key)
            event_reward = 0.0

            if record is not None:
                if record["objects"] == expected["objects"]:
                    event_reward += 0.7

                evidence = record["evidence"].lower()
                if any(keyword in evidence for keyword in expected["keywords"]):
                    event_reward += 0.3

            total_reward += event_reward
            print(
                f"{key[0]} @ {key[1]}: "
                f"matched={'yes' if record is not None else 'no'}, reward={event_reward:.2f}"
            )

        average_reward = total_reward / len(EXPECTED_EVENTS)
        _write_reward(average_reward)
        print(f"average_reward={average_reward:.6f}")

        assert average_reward > 0.0, "Reward must be positive for a structurally valid timeline"
    except Exception:
        _write_reward(0.0)
        raise
