import argparse
import csv
import json
import os
from pathlib import Path

OUTPUT_CSV = Path(os.environ.get("VOICE_CAST_LEDGER_CSV", "/root/voice_cast_ledger.csv"))
INPUT_JSON = Path(os.environ.get("AUDIOBOOK_INPUT_JSON", "/root/audiobook_dialogue_segments.json"))

EXPECTED_FIELDNAMES = [
    "row_type",
    "book_id",
    "voice_cast_id",
    "chapter_id",
    "chapter_number",
    "segment_id",
    "start_sec",
    "end_sec",
    "duration_sec",
    "chapter_count",
    "segment_count",
    "total_dialogue_duration_sec",
    "first_chapter_number",
    "transcript_excerpt",
]

EXPECTED_SUMMARIES = {
    "voice_cast_00": {
        "chapter_count": "3",
        "segment_count": "4",
        "total_dialogue_duration_sec": "6.34",
        "first_chapter_number": "1",
        "transcript_excerpt": "\"Hold the lantern higher,\" Aurelia whispered.",
    },
    "voice_cast_01": {
        "chapter_count": "2",
        "segment_count": "2",
        "total_dialogue_duration_sec": "2.87",
        "first_chapter_number": "1",
        "transcript_excerpt": "Bram answered, \"The river is closer than the map promised.\"",
    },
    "voice_cast_02": {
        "chapter_count": "3",
        "segment_count": "3",
        "total_dialogue_duration_sec": "4.74",
        "first_chapter_number": "1",
        "transcript_excerpt": "Cedric muttered, \"I heard the gate move.\"",
    },
}

EXPECTED_SEGMENT_CASTS = {
    "s01": "voice_cast_00",
    "s02": "voice_cast_01",
    "s04": "voice_cast_02",
    "s05": "voice_cast_00",
    "s06": "voice_cast_02",
    "s08": "voice_cast_00",
    "s09": "voice_cast_02",
    "s10": "voice_cast_00",
    "s12": "voice_cast_01",
}

EXCLUDED_SEGMENTS = {"s03", "s07", "s11"}


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def load_input_dialogue_segments():
    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    ordered = []
    for chapter in sorted(payload["chapters"], key=lambda item: item["chapter_number"]):
        for segment in sorted(chapter["segments"], key=lambda item: item["start_sec"]):
            if segment["role_hint"] != "dialogue":
                continue
            ordered.append(
                {
                    "book_id": payload["book_id"],
                    "chapter_id": chapter["chapter_id"],
                    "chapter_number": str(chapter["chapter_number"]),
                    "segment_id": segment["segment_id"],
                    "start_sec": f"{float(segment['start_sec']):.2f}",
                    "end_sec": f"{float(segment['end_sec']):.2f}",
                    "duration_sec": f"{float(segment['end_sec']) - float(segment['start_sec']):.2f}",
                    "transcript_excerpt": segment["transcript_excerpt"],
                }
            )
    return payload, ordered


def load_output_rows():
    expect(OUTPUT_CSV.exists(), "missing /root/voice_cast_ledger.csv")
    with OUTPUT_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expect(reader.fieldnames == EXPECTED_FIELDNAMES, "unexpected CSV header")
        return list(reader)


def pairwise_f1(actual_assignments):
    segment_ids = sorted(EXPECTED_SEGMENT_CASTS)
    true_positive = 0
    false_positive = 0
    false_negative = 0
    for left_index, left_segment in enumerate(segment_ids):
        for right_segment in segment_ids[left_index + 1 :]:
            expected_same = EXPECTED_SEGMENT_CASTS[left_segment] == EXPECTED_SEGMENT_CASTS[right_segment]
            actual_same = actual_assignments.get(left_segment) == actual_assignments.get(right_segment)
            if actual_same and expected_same:
                true_positive += 1
            elif actual_same and not expected_same:
                false_positive += 1
            elif not actual_same and expected_same:
                false_negative += 1
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def validate():
    payload, ordered_dialogue_segments = load_input_dialogue_segments()
    rows = load_output_rows()

    summary_rows = [row for row in rows if row["row_type"] == "cast_summary"]
    detail_rows = [row for row in rows if row["row_type"] == "segment_detail"]
    expect(len(summary_rows) == 3, "there must be exactly 3 cast_summary rows")
    expect(len(detail_rows) == len(ordered_dialogue_segments), "segment_detail row count mismatch")
    expect(rows[: len(summary_rows)] == summary_rows, "cast_summary rows must appear before segment_detail rows")

    expected_summary_order = sorted(EXPECTED_SUMMARIES)
    actual_summary_order = [row["voice_cast_id"] for row in summary_rows]
    expect(actual_summary_order == expected_summary_order, "cast_summary rows must be sorted by voice_cast_id")

    for row in rows:
        expect(row["book_id"] == payload["book_id"], "book_id mismatch")

    for row in summary_rows:
        voice_cast_id = row["voice_cast_id"]
        expect(voice_cast_id in EXPECTED_SUMMARIES, f"unexpected voice_cast_id in summary: {voice_cast_id}")
        expected = EXPECTED_SUMMARIES[voice_cast_id]
        expect(row["chapter_id"] == "", "summary chapter_id must be empty")
        expect(row["chapter_number"] == "", "summary chapter_number must be empty")
        expect(row["segment_id"] == "", "summary segment_id must be empty")
        expect(row["start_sec"] == "", "summary start_sec must be empty")
        expect(row["end_sec"] == "", "summary end_sec must be empty")
        expect(row["duration_sec"] == "", "summary duration_sec must be empty")
        for key, expected_value in expected.items():
            expect(row[key] == expected_value, f"summary {voice_cast_id} field mismatch: {key}")

    expected_detail_order = [
        (item["chapter_number"], item["start_sec"], item["segment_id"])
        for item in ordered_dialogue_segments
    ]
    actual_detail_order = [
        (row["chapter_number"], row["start_sec"], row["segment_id"])
        for row in detail_rows
    ]
    expect(actual_detail_order == expected_detail_order, "segment_detail rows must be sorted by chapter_number/start_sec")

    actual_assignments = {}
    for row, expected_segment in zip(detail_rows, ordered_dialogue_segments):
        segment_id = row["segment_id"]
        expect(segment_id == expected_segment["segment_id"], f"unexpected segment order: {segment_id}")
        expect(segment_id not in EXCLUDED_SEGMENTS, f"narration segment leaked into output: {segment_id}")
        expect(segment_id in EXPECTED_SEGMENT_CASTS, f"unexpected segment_id in output: {segment_id}")
        actual_assignments[segment_id] = row["voice_cast_id"]
        expect(row["chapter_id"] == expected_segment["chapter_id"], f"chapter_id mismatch for {segment_id}")
        expect(row["chapter_number"] == expected_segment["chapter_number"], f"chapter_number mismatch for {segment_id}")
        expect(row["start_sec"] == expected_segment["start_sec"], f"start_sec mismatch for {segment_id}")
        expect(row["end_sec"] == expected_segment["end_sec"], f"end_sec mismatch for {segment_id}")
        expect(row["duration_sec"] == expected_segment["duration_sec"], f"duration_sec mismatch for {segment_id}")
        expect(row["transcript_excerpt"] == expected_segment["transcript_excerpt"], f"transcript mismatch for {segment_id}")
        expect(row["chapter_count"] == "", f"detail chapter_count must be empty for {segment_id}")
        expect(row["segment_count"] == "", f"detail segment_count must be empty for {segment_id}")
        expect(row["total_dialogue_duration_sec"] == "", f"detail total_dialogue_duration_sec must be empty for {segment_id}")
        expect(row["first_chapter_number"] == "", f"detail first_chapter_number must be empty for {segment_id}")

    expect(actual_assignments == EXPECTED_SEGMENT_CASTS, "segment-to-cast assignment mismatch")

    return {
        "book_id": payload["book_id"],
        "summary_rows": len(summary_rows),
        "detail_rows": len(detail_rows),
        "all_assignments_correct": True,
    }


def write_score(score_path: Path):
    payload, ordered_dialogue_segments = load_input_dialogue_segments()
    result = {
        "book_id": payload["book_id"],
        "output_exists": OUTPUT_CSV.exists(),
        "dialogue_segment_count": len(ordered_dialogue_segments),
        "summary_rows": 0,
        "detail_rows": 0,
        "pairwise_f1": 0.0,
        "all_assignments_correct": False,
    }
    if OUTPUT_CSV.exists():
        try:
            rows = load_output_rows()
            detail_rows = [row for row in rows if row["row_type"] == "segment_detail"]
            actual_assignments = {
                row["segment_id"]: row["voice_cast_id"]
                for row in detail_rows
                if row["segment_id"]
            }
            result["summary_rows"] = len([row for row in rows if row["row_type"] == "cast_summary"])
            result["detail_rows"] = len(detail_rows)
            result["pairwise_f1"] = round(pairwise_f1(actual_assignments), 6)
            result["all_assignments_correct"] = actual_assignments == EXPECTED_SEGMENT_CASTS
        except Exception as exc:
            result["error"] = str(exc)
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", type=Path)
    args = parser.parse_args()
    if args.score is not None:
        write_score(args.score)
        return
    validate()


if __name__ == "__main__":
    main()
