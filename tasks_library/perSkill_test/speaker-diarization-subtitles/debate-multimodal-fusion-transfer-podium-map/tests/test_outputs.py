import csv
import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("PODIUM_OUTPUT_PATH", "/root/podium_speaking_times.csv"))
SEGMENTS_PATH = Path(os.environ.get("SPEECH_SEGMENTS_PATH", "/root/speech_segments.csv"))
WINDOWS_PATH = Path(os.environ.get("PODIUM_MOTION_WINDOWS_PATH", "/root/podium_motion_windows.json"))
AFFINITY_PATH = Path(os.environ.get("CLUSTER_SLOT_AFFINITY_PATH", "/root/cluster_slot_affinity.json"))
LAYOUT_PATH = Path(os.environ.get("STAGE_LAYOUT_PATH", "/root/stage_layout.json"))

FIELDNAMES = [
    "row_type",
    "slot_id",
    "segment_id",
    "start_sec",
    "end_sec",
    "duration_sec",
    "assignment_basis",
    "total_speaking_sec",
    "speaking_turns",
]


def load_segments(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def expected_rows() -> list[dict]:
    segments = load_segments(SEGMENTS_PATH)
    windows = load_json(WINDOWS_PATH)["windows"]
    affinity = load_json(AFFINITY_PATH)
    slots = sorted(load_json(LAYOUT_PATH)["slots"], key=lambda item: item["display_order"])
    slot_order = [item["slot_id"] for item in slots]
    slot_rank = {slot_id: index for index, slot_id in enumerate(slot_order)}

    def best_affinity_slot(cluster_name: str) -> str:
        scores = affinity[cluster_name]
        return max(slot_order, key=lambda slot_id: (scores[slot_id], -slot_rank[slot_id]))

    rows = []
    totals = {
        slot_id: {"total_speaking_sec": 0.0, "speaking_turns": 0}
        for slot_id in slot_order
    }

    for segment in segments:
        start_sec = float(segment["start_sec"])
        end_sec = float(segment["end_sec"])
        duration_sec = end_sec - start_sec
        lip_overlap = {slot_id: 0.0 for slot_id in slot_order}

        for window in windows:
            overlap_sec = overlap(start_sec, end_sec, float(window["start_sec"]), float(window["end_sec"]))
            if overlap_sec <= 0:
                continue
            for slot_id in window["lip_motion_slots"]:
                lip_overlap[slot_id] += overlap_sec

        ranked_visual = sorted(
            lip_overlap.items(),
            key=lambda item: (-item[1], slot_rank[item[0]]),
        )
        best_slot, best_overlap = ranked_visual[0]
        second_overlap = ranked_visual[1][1] if len(ranked_visual) > 1 else 0.0

        if best_overlap > second_overlap and (best_overlap / duration_sec) >= 0.5:
            assigned_slot = best_slot
            assignment_basis = "visual_lip_motion"
        else:
            assigned_slot = best_affinity_slot(segment["audio_cluster"])
            assignment_basis = "audio_cluster_fallback"

        rows.append(
            {
                "row_type": "segment",
                "slot_id": assigned_slot,
                "segment_id": segment["segment_id"],
                "start_sec": f"{start_sec:.2f}",
                "end_sec": f"{end_sec:.2f}",
                "duration_sec": f"{duration_sec:.2f}",
                "assignment_basis": assignment_basis,
                "total_speaking_sec": "",
                "speaking_turns": "",
            }
        )
        totals[assigned_slot]["total_speaking_sec"] += duration_sec
        totals[assigned_slot]["speaking_turns"] += 1

    for slot_id in slot_order:
        rows.append(
            {
                "row_type": "summary",
                "slot_id": slot_id,
                "segment_id": "",
                "start_sec": "",
                "end_sec": "",
                "duration_sec": "",
                "assignment_basis": "",
                "total_speaking_sec": f"{totals[slot_id]['total_speaking_sec']:.2f}",
                "speaking_turns": str(totals[slot_id]["speaking_turns"]),
            }
        )

    return rows


def test_output_exists_and_header_matches():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    fieldnames, _ = load_csv(OUTPUT_PATH)
    assert fieldnames == FIELDNAMES


def test_row_contract():
    _, rows = load_csv(OUTPUT_PATH)
    segments = load_segments(SEGMENTS_PATH)
    slots = sorted(load_json(LAYOUT_PATH)["slots"], key=lambda item: item["display_order"])
    slot_order = [item["slot_id"] for item in slots]

    assert len(rows) == len(segments) + len(slot_order)

    segment_rows = rows[: len(segments)]
    summary_rows = rows[len(segments) :]

    previous_start = None
    for row in segment_rows:
        assert row["row_type"] == "segment"
        assert row["slot_id"] in slot_order
        assert row["segment_id"]
        assert row["assignment_basis"] in {"visual_lip_motion", "audio_cluster_fallback"}
        assert row["total_speaking_sec"] == ""
        assert row["speaking_turns"] == ""
        start_sec = float(row["start_sec"])
        end_sec = float(row["end_sec"])
        duration_sec = float(row["duration_sec"])
        assert abs((end_sec - start_sec) - duration_sec) <= 1e-9
        if previous_start is not None:
            assert start_sec >= previous_start
        previous_start = start_sec

    for index, row in enumerate(summary_rows):
        assert row["row_type"] == "summary"
        assert row["slot_id"] == slot_order[index]
        assert row["segment_id"] == ""
        assert row["start_sec"] == ""
        assert row["end_sec"] == ""
        assert row["duration_sec"] == ""
        assert row["assignment_basis"] == ""
        assert float(row["total_speaking_sec"]) >= 0.0
        assert int(row["speaking_turns"]) >= 0


def test_expected_assignments_and_summary():
    _, rows = load_csv(OUTPUT_PATH)
    assert rows == expected_rows()
