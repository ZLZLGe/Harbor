#!/bin/bash
set -euo pipefail

python3 - <<'PY'
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


chapters = json.loads(INPUT_CHAPTERS.read_text(encoding="utf-8"))["chapters"]
voice_aliases = json.loads(INPUT_VOICES.read_text(encoding="utf-8"))

rows = []
concat_lines = []
global_idx = 0

for chapter_idx, chapter in enumerate(chapters, start=1):
    title = str(chapter["title"])
    voice_hint = str(chapter["voice_hint"])
    voice_id = str(voice_aliases[voice_hint])
    cleaned = clean_text(str(chapter["text"]))
    narration = f"Chapter: {title}. {cleaned}"
    chunks = sentence_chunk(narration, MAX_CHARS)

    for chunk_idx, chunk in enumerate(chunks, start=1):
        global_idx += 1
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

OUT_JSONL.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
OUT_CONCAT.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
PY
