#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
import os
import re
import subprocess
import wave
from pathlib import Path

CHAPTERS = [
    ("Do Things that Don't Scale", Path("/root/data/do-things.html")),
    ("Founder Mode", Path("/root/data/founder-mode.html")),
]

OUT_AUDIO = Path("/root/similar_audiobook.wav")
OUT_MANIFEST = Path("/root/similar_manifest.json")
TMP_DIR = Path("/tmp/similar_chunks")
TMP_DIR.mkdir(parents=True, exist_ok=True)


def pick_provider() -> str:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "gtts"


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


def synthesize_chunk(text: str, out_path: Path) -> None:
    subprocess.run(
        [
            "python3",
            "/root/tools/offline_tts.py",
            "--text",
            text,
            "--output",
            str(out_path),
        ],
        check=True,
    )


def concat_wavs(inputs: list[Path], output: Path) -> None:
    with wave.open(str(inputs[0]), "rb") as first:
        params = first.getparams()
        frames = [first.readframes(first.getnframes())]

    for path in inputs[1:]:
        with wave.open(str(path), "rb") as w:
            if w.getparams()[:3] != params[:3]:
                raise RuntimeError("Incompatible WAV parameters")
            frames.append(w.readframes(w.getnframes()))

    with wave.open(str(output), "wb") as out:
        out.setparams(params)
        for part in frames:
            out.writeframes(part)


all_chunk_files: list[Path] = []
chapter_titles: list[str] = []
total_clean_chars = 0

for chapter_idx, (title, chapter_file) in enumerate(CHAPTERS, start=1):
    raw_html = chapter_file.read_text(encoding="utf-8")
    cleaned = clean_text_for_narration(html_to_text(raw_html))
    chapter_titles.append(title)
    total_clean_chars += len(cleaned)

    chapter_text = f"Chapter: {title}. {cleaned}"
    chunks = chunk_text(chapter_text, max_chars=220)

    for chunk_idx, chunk in enumerate(chunks, start=1):
        out_chunk = TMP_DIR / f"chapter{chapter_idx:02d}_chunk{chunk_idx:03d}.wav"
        synthesize_chunk(chunk, out_chunk)
        all_chunk_files.append(out_chunk)

if not all_chunk_files:
    raise RuntimeError("No chunk audio generated")

concat_wavs(all_chunk_files, OUT_AUDIO)

manifest = {
    "provider": pick_provider(),
    "chapter_titles": chapter_titles,
    "chapter_count": len(chapter_titles),
    "total_chunks": len(all_chunk_files),
    "total_clean_chars": total_clean_chars,
}
OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY
