#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import csv
import json
import re
import subprocess
import wave
from pathlib import Path

OUT_AUDIO = Path('/root/transfer1_city_briefing.wav')
OUT_CSV = Path('/root/transfer1_chapter_stats.csv')
TMP_DIR = Path('/tmp/transfer1_chunks')
TMP_DIR.mkdir(parents=True, exist_ok=True)


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"^\s*#+\s+.*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, max_chars: int = 180) -> list[str]:
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
    subprocess.run([
        'python3', '/root/tools/offline_tts.py', '--text', text, '--output', str(out_path)
    ], check=True)


def concat_wavs(inputs: list[Path], output: Path) -> None:
    with wave.open(str(inputs[0]), 'rb') as first:
        params = first.getparams()
        frames = [first.readframes(first.getnframes())]
    for path in inputs[1:]:
        with wave.open(str(path), 'rb') as w:
            if w.getparams()[:3] != params[:3]:
                raise RuntimeError('Incompatible WAV parameters')
            frames.append(w.readframes(w.getnframes()))
    with wave.open(str(output), 'wb') as out:
        out.setparams(params)
        for part in frames:
            out.writeframes(part)


playlist = json.loads(Path('/root/data/playlist_order.json').read_text(encoding='utf-8'))['items']
all_chunks: list[Path] = []
rows: list[dict[str, str]] = []

for chapter_idx, item in enumerate(playlist, start=1):
    title = item['title']
    raw = Path('/root/data', item['file']).read_text(encoding='utf-8')
    cleaned = clean_markdown(raw)
    narration = f"Briefing: {title}. {cleaned}"
    chunks = chunk_text(narration, max_chars=180)

    rows.append({
        'chapter_title': title,
        'char_count': str(len(cleaned)),
        'chunk_count': str(len(chunks)),
    })

    for chunk_idx, chunk in enumerate(chunks, start=1):
        out_chunk = TMP_DIR / f"ch{chapter_idx:02d}_{chunk_idx:03d}.wav"
        synthesize_chunk(chunk, out_chunk)
        all_chunks.append(out_chunk)

if not all_chunks:
    raise RuntimeError('No chunk audio generated')

concat_wavs(all_chunks, OUT_AUDIO)

with OUT_CSV.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['chapter_title', 'char_count', 'chunk_count'])
    writer.writeheader()
    writer.writerows(rows)
PY
