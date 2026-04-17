import json
import re
import subprocess
from pathlib import Path

DATA_DIR = Path("/root/data")
AUDIO_PATH = Path("/root/briefing_digest.mp3")
INDEX_PATH = Path("/root/briefing_index.json")
MAX_CHARS = 210

BRIEFINGS = {
    "alpha": DATA_DIR / "briefing_alpha.md",
    "beta": DATA_DIR / "briefing_beta.md",
    "gamma": DATA_DIR / "briefing_gamma.md",
}


def parse_markdown(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = "Untitled Briefing"
    body_parts: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.*)$", stripped)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            if title == "Untitled Briefing":
                title = heading_text
            else:
                body_parts.append(heading_text)
            continue
        stripped = re.sub(r"^-\s+", "", stripped)
        body_parts.append(stripped)
    body = " ".join(body_parts)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"\[\d+\]", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return title, body


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


def expected_payload() -> tuple[list[str], list[str], dict[str, int], int, int]:
    order = json.loads((DATA_DIR / "playlist_order.json").read_text(encoding="utf-8"))["order"]
    ordered_titles: list[str] = []
    chunk_counts: dict[str, int] = {}
    total_input_chars = 0
    total_chunks = 0

    for briefing_id in order:
        title, body = parse_markdown(BRIEFINGS[briefing_id])
        ordered_titles.append(title)
        total_input_chars += len(body)
        chunks = chunk_text(f"Briefing: {title}. {body}", MAX_CHARS)
        chunk_counts[briefing_id] = len(chunks)
        total_chunks += len(chunks)

    return order, ordered_titles, chunk_counts, total_chunks, total_input_chars


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f"missing audio file: {AUDIO_PATH}"
    assert INDEX_PATH.exists(), f"missing index file: {INDEX_PATH}"

    payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    order, titles, chunk_counts, total_chunks, total_input_chars = expected_payload()

    assert payload.get("provider") in {"gtts", "hybrid", "offline-fallback"}
    assert payload.get("ordered_ids") == order
    assert payload.get("ordered_titles") == titles
    assert payload.get("chunk_counts") == chunk_counts
    assert payload.get("total_chunks") == total_chunks
    assert payload.get("total_input_chars") == total_input_chars

    gtts_chunk_count = payload.get("gtts_chunk_count")
    assert isinstance(gtts_chunk_count, int)
    assert 0 <= gtts_chunk_count <= total_chunks

    assert AUDIO_PATH.stat().st_size > 4000, "audio output too small"
    assert duration_seconds(AUDIO_PATH) > 6.0, "audio output too short"


if __name__ == "__main__":
    test_outputs()
    print("transfer1 checks passed")
