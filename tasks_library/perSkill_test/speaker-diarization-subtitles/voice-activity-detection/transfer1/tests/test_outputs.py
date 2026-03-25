import csv


OUTPUT_PATH = "/root/review_silence_windows.csv"


def test_review_silence_windows():
    with open(OUTPUT_PATH, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected = [
        {
            "silence_id": "silence_01",
            "start_sec": "54.0",
            "end_sec": "54.99",
            "duration_sec": "0.99",
            "left_context": "START",
            "right_context": "speech_01",
        },
        {
            "silence_id": "silence_02",
            "start_sec": "55.82",
            "end_sec": "56.36",
            "duration_sec": "0.54",
            "left_context": "speech_01",
            "right_context": "speech_02",
        },
        {
            "silence_id": "silence_03",
            "start_sec": "57.694",
            "end_sec": "59.59",
            "duration_sec": "1.896",
            "left_context": "speech_03",
            "right_context": "speech_04",
        },
        {
            "silence_id": "silence_04",
            "start_sec": "60.071",
            "end_sec": "60.546",
            "duration_sec": "0.475",
            "left_context": "speech_04",
            "right_context": "speech_05",
        },
        {
            "silence_id": "silence_05",
            "start_sec": "61.534",
            "end_sec": "63.386",
            "duration_sec": "1.852",
            "left_context": "speech_05",
            "right_context": "speech_06",
        },
        {
            "silence_id": "silence_06",
            "start_sec": "63.766",
            "end_sec": "65.698",
            "duration_sec": "1.932",
            "left_context": "speech_06",
            "right_context": "speech_07",
        },
    ]

    assert rows == expected
