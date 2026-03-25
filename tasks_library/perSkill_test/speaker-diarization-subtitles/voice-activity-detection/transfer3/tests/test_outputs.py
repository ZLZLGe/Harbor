import json


OUTPUT_PATH = "/root/activity_burst_audit.json"


def test_activity_burst_audit():
    with open(OUTPUT_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)

    expected = {
        "kept_segment_count": 14,
        "total_speech_sec": 11.564,
        "first_speech_sec": 0.804,
        "last_speech_sec": 66.366,
        "longest_quiet_gap_sec": 30.0,
        "segments_after_quiet_gap": [
            {"segment_id": "speech_02", "gap_sec": 4.846},
            {"segment_id": "speech_06", "gap_sec": 4.352},
            {"segment_id": "speech_07", "gap_sec": 5.67},
            {"segment_id": "speech_08", "gap_sec": 30.0},
        ],
        "micro_bursts": ["speech_09", "speech_10", "speech_11", "speech_13"],
        "phase_totals_sec": {
            "phase_1_under_30": 7.254,
            "phase_2_30_to_60": 2.274,
            "phase_3_60_plus": 2.036,
        },
    }

    assert payload == expected
