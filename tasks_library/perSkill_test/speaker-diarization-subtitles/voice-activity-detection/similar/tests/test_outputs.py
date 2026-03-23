import json


OUTPUT_PATH = "/root/final_speech_segments.json"


def test_final_speech_segments():
    with open(OUTPUT_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)

    expected = {
        "clip_id": "lobby_scene_subtitle_prep",
        "segment_count": 7,
        "total_speech_sec": 7.254,
        "first_start_sec": 0.804,
        "last_end_sec": 24.99,
        "speech_segments": [
            {
                "segment_id": "speech_01",
                "start_sec": 0.804,
                "end_sec": 1.664,
                "duration_sec": 0.86,
                "source_ids": ["a1", "a2"],
            },
            {
                "segment_id": "speech_02",
                "start_sec": 6.51,
                "end_sec": 7.44,
                "duration_sec": 0.93,
                "source_ids": ["a4", "a5"],
            },
            {
                "segment_id": "speech_03",
                "start_sec": 8.21,
                "end_sec": 9.31,
                "duration_sec": 1.1,
                "source_ids": ["a6", "a7"],
            },
            {
                "segment_id": "speech_04",
                "start_sec": 9.71,
                "end_sec": 10.956,
                "duration_sec": 1.246,
                "source_ids": ["a8", "a9"],
            },
            {
                "segment_id": "speech_05",
                "start_sec": 11.85,
                "end_sec": 12.55,
                "duration_sec": 0.7,
                "source_ids": ["a10"],
            },
            {
                "segment_id": "speech_06",
                "start_sec": 16.902,
                "end_sec": 18.15,
                "duration_sec": 1.248,
                "source_ids": ["a11", "a12"],
            },
            {
                "segment_id": "speech_07",
                "start_sec": 23.82,
                "end_sec": 24.99,
                "duration_sec": 1.17,
                "source_ids": ["a14", "a15"],
            },
        ],
    }

    assert payload == expected
