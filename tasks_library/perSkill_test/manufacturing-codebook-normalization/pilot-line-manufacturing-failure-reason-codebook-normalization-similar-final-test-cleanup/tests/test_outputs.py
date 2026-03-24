#!/usr/bin/env python3
import json
import os
from statistics import mean

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

EVENTS_PATH = os.path.join(DATA_DIR, "pilot_line_events.jsonl")
CODEBOOK_PATH = os.path.join(DATA_DIR, "reason_codebooks.json")
OUTPUT_PATH = os.path.join(OUT_DIR, "final_test_reason_map.json")
UNKNOWN = "UNKNOWN"

EXPECTED = {
    "EVT-1001": [
        ("12V output dead，J9开路样子", "AX5-FT-001"),
        ("U17脚位浮高", "AX5-SD-004"),
    ],
    "EVT-1002": [
        ("fan不转，tach no pulse，重测还是挂", "AX5-FT-002"),
    ],
    "EVT-1003": [
        ("老化2h后 OTP trip，自动关机", "AX5-BI-005"),
    ],
    "EVT-1004": [
        ("静态电流偏高，像半短路", "AX5-FT-003"),
    ],
    "EVT-1005": [
        ("换夹具后偶尔OK，治具接触飘", "AX5-GN-006"),
    ],
    "EVT-1006": [
        ("CRC对不上，fw pkg mismatch", "BZ9-FT-001"),
    ],
    "EVT-1007": [
        ("写eeprom失败，重烧也不稳", "BZ9-FT-003"),
    ],
    "EVT-1008": [
        ("CAN timeout at J3，偶发丢包", "BZ9-FT-002"),
    ],
    "EVT-1009": [
        ("老化时 watchdog reset loop", "BZ9-BI-004"),
        ("TP12 浮高", "BZ9-SD-005"),
    ],
    "EVT-1010": [
        ("probe pin worn, contact bad", "BZ9-GN-006"),
    ],
    "EVT-1011": [
        ("老化时灯闪一下就灭, maybe cap issue", UNKNOWN),
    ],
    "EVT-1012": [
        ("J3附近有点怪，debug later", UNKNOWN),
    ],
    "EVT-1013": [
        ("静态电流高", "AX5-FT-003"),
        ("reseat治具后有时过", "AX5-GN-006"),
    ],
    "EVT-1014": [
        ("CRC fail", "BZ9-FT-001"),
        ("probe wear again", "BZ9-GN-006"),
    ],
}


def load_events():
    events = {}
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            events[row["event_id"]] = row
    return events


def load_codebooks():
    with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    labels = {}
    scopes = {}
    for product in raw["products"]:
        pid = product["product_id"]
        labels[pid] = {}
        scopes[pid] = {}
        for entry in product["entries"]:
            labels[pid][entry["code"]] = entry["standard_label"]
            scopes[pid][entry["code"]] = set(entry.get("station_scope", []))
    return labels, scopes


def load_output():
    assert os.path.exists(OUTPUT_PATH), f"Missing required output: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def segments_of(record):
    segs = record.get("reason_segments")
    assert isinstance(segs, list), f"reason_segments must be a list for {record.get('event_id')}"
    return segs


def test_output_file_exists_and_is_json():
    payload = load_output()
    assert isinstance(payload, dict), "Output must be a JSON object"
    assert isinstance(payload.get("records"), list), "Output must contain records list"


def test_all_events_present_without_extra_records():
    payload = load_output()
    records = payload["records"]
    event_ids = [record.get("event_id") for record in records]
    assert set(event_ids) == set(EXPECTED), "Output must cover all input events exactly"
    assert len(event_ids) == len(set(event_ids)), "event_id must be unique"


def test_record_fields_echo_input():
    events = load_events()
    payload = load_output()
    for record in payload["records"]:
        event = events[record["event_id"]]
        for key in ["product_id", "station", "engineer_id", "test_item", "symptom_code", "raw_reason_text"]:
            assert record.get(key) == event.get(key), f"{record['event_id']} field mismatch on {key}"


def test_segment_ids_and_spans_are_exact():
    payload = load_output()
    events = load_events()
    for record in payload["records"]:
        event_id = record["event_id"]
        raw = events[event_id]["raw_reason_text"]
        expected = EXPECTED[event_id]
        segs = segments_of(record)
        assert len(segs) == len(expected), f"{event_id} should have {len(expected)} segments"
        for idx, (segment, (span_text, _)) in enumerate(zip(segs, expected), start=1):
            assert segment.get("segment_id") == f"{event_id}-S{idx}"
            assert segment.get("span_text") == span_text
            assert span_text in raw, f"{event_id} span must be exact substring"


def test_exact_codes_and_labels_match_expected():
    payload = load_output()
    labels, _ = load_codebooks()
    for record in payload["records"]:
        product_id = record["product_id"]
        expected = EXPECTED[record["event_id"]]
        for segment, (_, code) in zip(segments_of(record), expected):
            assert segment.get("pred_code") == code, f"{record['event_id']} predicted wrong code"
            if code == UNKNOWN:
                assert segment.get("pred_label") == ""
            else:
                assert segment.get("pred_label") == labels[product_id][code]


def test_station_scope_is_respected_for_known_predictions():
    payload = load_output()
    _, scopes = load_codebooks()
    for record in payload["records"]:
        station = record["station"]
        product_id = record["product_id"]
        for segment in segments_of(record):
            code = segment["pred_code"]
            if code == UNKNOWN:
                continue
            assert station in scopes[product_id][code], f"{record['event_id']} uses out-of-scope code {code}"


def test_confidence_is_numeric_rounded_and_separated():
    payload = load_output()
    known = []
    unknown = []
    for record in payload["records"]:
        for segment in segments_of(record):
            confidence = segment.get("confidence")
            assert isinstance(confidence, (int, float)), "confidence must be numeric"
            assert 0.0 <= float(confidence) <= 1.0, "confidence out of range"
            assert round(float(confidence), 4) == float(confidence), "confidence must be rounded to 4 decimals"
            if segment["pred_code"] == UNKNOWN:
                unknown.append(float(confidence))
            else:
                known.append(float(confidence))
    assert known and unknown, "Task should contain both known and UNKNOWN predictions"
    assert mean(known) > mean(unknown), "Known predictions should be more confident on average"
    assert max(unknown) < min(known), "UNKNOWN confidence should stay below known confidence for this dataset"


def test_rationale_is_non_empty_and_mentions_context():
    payload = load_output()
    for record in payload["records"]:
        station = record["station"]
        test_item = record["test_item"]
        symptom_code = record["symptom_code"]
        for segment in segments_of(record):
            rationale = str(segment.get("rationale", "")).strip()
            assert rationale, f"{record['event_id']} rationale must not be empty"
            assert station in rationale, f"{record['event_id']} rationale should mention station"
            assert test_item in rationale or symptom_code in rationale, f"{record['event_id']} rationale should mention context"


def run_all():
    tests = [
        test_output_file_exists_and_is_json,
        test_all_events_present_without_extra_records,
        test_record_fields_echo_input,
        test_segment_ids_and_spans_are_exact,
        test_exact_codes_and_labels_match_expected,
        test_station_scope_is_respected_for_known_predictions,
        test_confidence_is_numeric_rounded_and_separated,
        test_rationale_is_non_empty_and_mentions_context,
    ]
    for test in tests:
        test()


if __name__ == "__main__":
    run_all()
    print("all checks passed")
