import json
import re
import wave
from pathlib import Path

AUDIO_PATH = Path("/root/similar_audiobook.wav")
MANIFEST_PATH = Path("/root/similar_manifest.json")
CHAPTERS = [
    ("Do Things that Don't Scale", Path("/root/data/do-things.html")),
    ("Founder Mode", Path("/root/data/founder-mode.html")),
]


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_text_for_narration(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, max_chars: int = 220) -> list[str]:
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


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def expected_values() -> tuple[list[str], int, int]:
    titles = []
    total_clean_chars = 0
    total_chunks = 0
    for title, chapter_file in CHAPTERS:
        raw_html = chapter_file.read_text(encoding="utf-8")
        cleaned = clean_text_for_narration(html_to_text(raw_html))
        total_clean_chars += len(cleaned)
        chapter_text = f"Chapter: {title}. {cleaned}"
        chunks = chunk_text(chapter_text, max_chars=220)
        total_chunks += len(chunks)
        titles.append(title)
    return titles, total_chunks, total_clean_chars


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f"missing audio output: {AUDIO_PATH}"
    assert MANIFEST_PATH.exists(), f"missing manifest output: {MANIFEST_PATH}"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    titles, total_chunks, total_clean_chars = expected_values()

    assert manifest.get("provider") == "gtts"
    assert manifest.get("chapter_titles") == titles
    assert manifest.get("chapter_count") == 2
    assert manifest.get("total_chunks") == total_chunks
    assert manifest.get("total_clean_chars") == total_clean_chars

    assert AUDIO_PATH.stat().st_size > 20000, "audio output is unexpectedly small"
    duration = wav_duration(AUDIO_PATH)
    assert duration > 8.0, f"audio duration too short: {duration}"


if __name__ == "__main__":
    test_outputs()
    print("similar checks passed")
