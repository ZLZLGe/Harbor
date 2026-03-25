import csv


OUTPUT_PATH = "/root/pickup_cues.tsv"


def test_pickup_cues():
    with open(OUTPUT_PATH, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    expected = [
        {
            "cue_id": "cue_01",
            "start_sec": "0.604",
            "end_sec": "2.014",
            "duration_sec": "1.41",
            "source_segment_count": "1",
            "source_segments": "speech_01",
        },
        {
            "cue_id": "cue_02",
            "start_sec": "6.31",
            "end_sec": "7.79",
            "duration_sec": "1.48",
            "source_segment_count": "1",
            "source_segments": "speech_02",
        },
        {
            "cue_id": "cue_03",
            "start_sec": "8.01",
            "end_sec": "11.306",
            "duration_sec": "3.296",
            "source_segment_count": "2",
            "source_segments": "speech_03;speech_04",
        },
        {
            "cue_id": "cue_04",
            "start_sec": "11.65",
            "end_sec": "12.9",
            "duration_sec": "1.25",
            "source_segment_count": "1",
            "source_segments": "speech_05",
        },
        {
            "cue_id": "cue_05",
            "start_sec": "16.702",
            "end_sec": "18.5",
            "duration_sec": "1.798",
            "source_segment_count": "1",
            "source_segments": "speech_06",
        },
        {
            "cue_id": "cue_06",
            "start_sec": "23.62",
            "end_sec": "25.2",
            "duration_sec": "1.58",
            "source_segment_count": "1",
            "source_segments": "speech_07",
        },
    ]

    assert rows == expected
