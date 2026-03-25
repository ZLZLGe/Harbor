import csv
import json
from pathlib import Path


ROOT = Path("/root")
OUTPUT_PATH = ROOT / "event_windows.json"
MANIFEST_PATH = ROOT / "patrol_manifest.json"
EVENT_LOG_PATH = ROOT / "robot_event_log.csv"


def load_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_events() -> list[tuple[str, int, int]]:
    rows = []
    with open(EVENT_LOG_PATH, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append((row["event"], int(row["start_ms"]), int(row["end_ms"])))
    return rows


def parse_interval_key(key: str) -> tuple[int, int]:
    start_str, end_str = key.split("->")
    return int(start_str), int(end_str)


def derive_expected_windows() -> list[tuple[int, int, list[str]]]:
    manifest = load_manifest()
    events = load_events()

    sample_count = int(manifest["sample_count"])
    sample_origin_ms = int(manifest["sample_origin_ms"])
    sample_period_ms = int(manifest["sample_period_ms"])

    per_sample = []
    for i in range(sample_count):
        timestamp_ms = sample_origin_ms + i * sample_period_ms
        active = sorted({event for event, start_ms, end_ms in events if start_ms <= timestamp_ms < end_ms})
        per_sample.append(active or ["clear"])

    merged = []
    start = 0
    current = per_sample[0]
    for i in range(1, sample_count + 1):
        if i == sample_count or per_sample[i] != current:
            merged.append((start, i, current))
            if i < sample_count:
                start = i
                current = per_sample[i]
    return merged


def load_prediction() -> dict:
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_prediction(pred: dict) -> list[tuple[int, int, list[str]]]:
    normalized = []
    for key, value in pred.items():
        start, end = parse_interval_key(key)
        normalized.append((start, end, value))
    normalized.sort(key=lambda item: item[0])
    return normalized


def test_output_exists():
    assert OUTPUT_PATH.exists(), "Missing /root/event_windows.json"


def test_schema_and_coverage():
    manifest = load_manifest()
    valid_labels = {event for event, _, _ in load_events()} | {"clear"}
    pred = load_prediction()

    assert isinstance(pred, dict), "event_windows.json must be a JSON object"
    assert pred, "event_windows.json must not be empty"

    normalized = normalize_prediction(pred)
    cursor = 0
    for start, end, value in normalized:
        assert 0 <= start < end <= int(manifest["sample_count"])
        assert start == cursor, "intervals must be contiguous and ordered"
        assert isinstance(value, list) and value, "each value must be a non-empty string array"
        assert value == sorted(set(value)), "event arrays must be deduplicated and sorted"
        assert set(value) <= valid_labels, "unknown event label found"
        if "clear" in value:
            assert value == ["clear"], "clear must appear alone"
        cursor = end

    assert cursor == int(manifest["sample_count"]), "intervals must cover the full sample domain"

    for (_, end_a, value_a), (start_b, _, value_b) in zip(normalized, normalized[1:]):
        assert end_a == start_b
        assert value_a != value_b, "adjacent identical event arrays must be merged"


def test_projection_matches_assets():
    expected = derive_expected_windows()
    pred = normalize_prediction(load_prediction())
    assert pred == expected
