import csv
import json
import re
import subprocess
from pathlib import Path

DATA_DIR = Path("/root/data")
AUDIO_PATH = Path("/root/casefile_narration.mp3")
SEGMENTS_PATH = Path("/root/casefile_segments.json")
MAX_CHARS = 190


def chunk_text(text: str, max_chars: int) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= max_chars:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def duration_seconds(audio_file: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(result.stdout.strip())


def expected_payload() -> tuple[list[str], list[str], int, dict[str, int], int]:
    phase_order = json.loads((DATA_DIR / "phase_order.json").read_text(encoding="utf-8"))["order"]
    phase_rank = {phase: idx for idx, phase in enumerate(phase_order)}

    rows = []
    with (DATA_DIR / "casefile_fragments.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            rows.append(
                {
                    "case_id": row["case_id"].strip(),
                    "phase": row["phase"].strip(),
                    "note": re.sub(r"\s+", " ", row["note"].strip()),
                    "_idx": idx,
                }
            )

    rows.sort(key=lambda r: (r["case_id"], phase_rank.get(r["phase"], len(phase_rank)), r["_idx"]))

    case_ids = sorted({r["case_id"] for r in rows})
    chars_per_case = {cid: 0 for cid in case_ids}
    narration_segments: list[str] = []
    current_case = None

    for row in rows:
        cid = row["case_id"]
        phase = row["phase"]
        note = row["note"]

        if cid != current_case:
            narration_segments.append(f"Case {cid} summary.")
            current_case = cid

        narration_segments.append(f"Case {cid}, {phase} phase: {note}.")
        chars_per_case[cid] += len(note)

    chunks = chunk_text(" ".join(narration_segments), MAX_CHARS)
    return case_ids, phase_order, len(rows), chars_per_case, len(chunks)


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f"missing audio file: {AUDIO_PATH}"
    assert SEGMENTS_PATH.exists(), f"missing summary file: {SEGMENTS_PATH}"

    payload = json.loads(SEGMENTS_PATH.read_text(encoding="utf-8"))
    case_ids, phase_order, segment_count, chars_per_case, total_chunks = expected_payload()

    assert payload.get("provider") in {"gtts", "hybrid", "offline-fallback"}
    assert payload.get("case_ids") == case_ids
    assert payload.get("phase_order") == phase_order
    assert payload.get("segment_count") == segment_count
    assert payload.get("chars_per_case") == chars_per_case
    assert payload.get("total_chunks") == total_chunks

    gtts_chunk_count = payload.get("gtts_chunk_count")
    assert isinstance(gtts_chunk_count, int)
    assert 0 <= gtts_chunk_count <= total_chunks

    assert AUDIO_PATH.stat().st_size > 3500, "audio output too small"
    assert duration_seconds(AUDIO_PATH) > 5.0, "audio output too short"


if __name__ == "__main__":
    test_outputs()
    print("transfer3 checks passed")
