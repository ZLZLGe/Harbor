import json
import re
import subprocess
from pathlib import Path

AUDIO_PATH = Path("/root/audiobook.mp3")
MANIFEST_PATH = Path("/root/audiobook_manifest.json")
MAX_CHARS = 260
CHAPTERS = [
    ("Do Things that Don't Scale", Path("/root/data/do-things.html")),
    ("Founder Mode", Path("/root/data/founder-mode.html")),
]


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


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
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_file),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def expected_values() -> tuple[list[str], int, int]:
    titles: list[str] = []
    total_chunks = 0
    total_chars = 0
    for title, path in CHAPTERS:
        cleaned = clean_text(html_to_text(path.read_text(encoding="utf-8")))
        total_chars += len(cleaned)
        titles.append(title)
        chapter_text = f"Chapter: {title}. {cleaned}"
        total_chunks += len(chunk_text(chapter_text, MAX_CHARS))
    return titles, total_chunks, total_chars


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f"missing audio output: {AUDIO_PATH}"
    assert MANIFEST_PATH.exists(), f"missing manifest output: {MANIFEST_PATH}"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    titles, total_chunks, total_chars = expected_values()

    assert manifest.get("provider") in {"gtts", "hybrid", "offline-fallback"}
    assert manifest.get("chapter_titles") == titles
    assert manifest.get("chapter_count") == 2
    assert manifest.get("total_chunks") == total_chunks
    assert manifest.get("total_clean_chars") == total_chars

    gtts_chunk_count = manifest.get("gtts_chunk_count")
    assert isinstance(gtts_chunk_count, int)
    assert 0 <= gtts_chunk_count <= total_chunks
    if manifest.get("provider") == "gtts":
        assert gtts_chunk_count == total_chunks
    if manifest.get("provider") == "offline-fallback":
        assert gtts_chunk_count == 0

    assert AUDIO_PATH.stat().st_size > 5000, "audio output too small"
    assert duration_seconds(AUDIO_PATH) > 8.0, "audio output too short"


if __name__ == "__main__":
    test_outputs()
    print("similar checks passed")
