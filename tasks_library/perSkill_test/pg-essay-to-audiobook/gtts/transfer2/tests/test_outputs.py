import json
import re
import subprocess
from pathlib import Path

DATA_DIR = Path("/root/data")
AUDIO_PATH = Path("/root/call_recap.mp3")
REPORT_PATH = Path("/root/call_recap_report.json")
MAX_CHARS = 170


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


def expected_payload() -> tuple[list[str], int, list[str], dict[str, int], int]:
    severity_order = json.loads((DATA_DIR / "severity_order.json").read_text(encoding="utf-8"))["order"]
    rank = {name: idx for idx, name in enumerate(severity_order)}

    items = []
    for idx, raw in enumerate((DATA_DIR / "call_snippets.jsonl").read_text(encoding="utf-8").splitlines()):
        line = raw.strip()
        if not line:
            continue
        payload = json.loads(line)
        payload["_idx"] = idx
        payload["text"] = re.sub(r"\s+", " ", payload["text"]).strip()
        items.append(payload)

    items.sort(key=lambda x: (rank.get(x["severity"], len(rank)), x["_idx"]))

    narration: list[str] = []
    chars_by_severity = {name: 0 for name in severity_order}
    for sev in severity_order:
        group = [it for it in items if it["severity"] == sev]
        if not group:
            continue
        narration.append(f"Priority {sev} updates.")
        for entry in group:
            narration.append(f"{entry['speaker']} from {entry['case_id']} reports: {entry['text']}.")
            chars_by_severity[sev] += len(entry["text"])

    chunks = chunk_text(" ".join(narration), MAX_CHARS)
    return severity_order, len(items), sorted({it["case_id"] for it in items}), chars_by_severity, len(chunks)


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f"missing audio file: {AUDIO_PATH}"
    assert REPORT_PATH.exists(), f"missing report file: {REPORT_PATH}"

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    severity_order, item_count, unique_cases, chars_by_severity, total_chunks = expected_payload()

    assert report.get("provider") in {"gtts", "hybrid", "offline-fallback"}
    assert report.get("severity_order") == severity_order
    assert report.get("item_count") == item_count
    assert report.get("unique_cases") == unique_cases
    assert report.get("chars_by_severity") == chars_by_severity
    assert report.get("total_chunks") == total_chunks

    gtts_chunk_count = report.get("gtts_chunk_count")
    assert isinstance(gtts_chunk_count, int)
    assert 0 <= gtts_chunk_count <= total_chunks

    assert AUDIO_PATH.stat().st_size > 3500, "audio output too small"
    assert duration_seconds(AUDIO_PATH) > 5.0, "audio output too short"


if __name__ == "__main__":
    test_outputs()
    print("transfer2 checks passed")
