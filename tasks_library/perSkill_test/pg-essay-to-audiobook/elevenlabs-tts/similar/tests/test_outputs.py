import json
import re
from pathlib import Path

INPUT_CHAPTERS = Path("/root/data/essay_packets.json")
INPUT_VOICES = Path("/root/data/voice_aliases.json")
OUT_JSONL = Path("/root/similar_elevenlabs_requests.jsonl")
OUT_CONCAT = Path("/root/similar_concat_manifest.txt")
MAX_CHARS = 1200


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sentence_chunk(text: str, limit: int) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(sentence), limit):
                part = sentence[i : i + limit].strip()
                if part:
                    chunks.append(part)
            continue
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= limit:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def expected_rows_and_concat() -> tuple[list[dict], list[str]]:
    chapters = json.loads(INPUT_CHAPTERS.read_text(encoding="utf-8"))["chapters"]
    aliases = json.loads(INPUT_VOICES.read_text(encoding="utf-8"))

    rows: list[dict] = []
    concat_lines: list[str] = []
    for chapter_idx, chapter in enumerate(chapters, start=1):
        title = str(chapter["title"])
        voice_id = str(aliases[str(chapter["voice_hint"])])
        cleaned = clean_text(str(chapter["text"]))
        narration = f"Chapter: {title}. {cleaned}"
        chunks = sentence_chunk(narration, MAX_CHARS)
        for chunk_idx, chunk in enumerate(chunks, start=1):
            rows.append(
                {
                    "chapter_title": title,
                    "chunk_index": chunk_idx,
                    "voice_id": voice_id,
                    "url": f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    "headers": {
                        "xi-api-key": "${ELEVENLABS_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    "body": {
                        "text": chunk,
                        "model_id": "eleven_turbo_v2_5",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    },
                }
            )
            concat_lines.append(f"file 'chapter{chapter_idx:02d}_chunk{chunk_idx:03d}.mp3'")
    return rows, concat_lines


def test_outputs() -> None:
    assert OUT_JSONL.exists(), f"missing output: {OUT_JSONL}"
    assert OUT_CONCAT.exists(), f"missing output: {OUT_CONCAT}"

    lines = [line.strip() for line in OUT_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    actual_rows = [json.loads(line) for line in lines]
    expected_rows, expected_concat = expected_rows_and_concat()

    assert actual_rows == expected_rows, "request JSONL content mismatch"
    for row in actual_rows:
        assert len(row["body"]["text"]) <= MAX_CHARS

    concat_lines = [line.strip() for line in OUT_CONCAT.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert concat_lines == expected_concat, "concat manifest mismatch"


if __name__ == "__main__":
    test_outputs()
    print("similar checks passed")
