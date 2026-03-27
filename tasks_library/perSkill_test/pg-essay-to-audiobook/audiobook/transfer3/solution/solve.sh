#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import csv
import re
import subprocess
import wave
from pathlib import Path

OUT_AUDIO = Path('/root/transfer3_casefile_audio.wav')
OUT_CUES = Path('/root/transfer3_cues.txt')
TMP_DIR = Path('/tmp/transfer3_chunks')
TMP_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def chunk_text(text: str, max_chars: int = 200) -> list[str]:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    chunks: list[str] = []
    current = ''
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


rows = []
with Path('/root/data/casefile_fragments.csv').open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        rows.append(row)

rows.sort(key=lambda r: (str(r['section']), int(r['rank'])))

kept = []
seen = set()
for row in rows:
    cleaned = clean_text(str(row['text']))
    key = cleaned.lower()
    if key in seen:
        continue
    seen.add(key)
    kept.append((str(row['section']), cleaned))

narration_parts = []
cue_lines = []
current_section = None
for idx, (section, cleaned) in enumerate(kept, start=1):
    if section != current_section:
        narration_parts.append(f"Section {section}.")
        current_section = section
    narration_parts.append(f"{section}: {cleaned}.")
    cue_lines.append(f"{idx}|{section}|{len(cleaned)}")

narration = ' '.join(narration_parts).strip()
chunks = chunk_text(narration, max_chars=200)

chunk_paths: list[Path] = []
for idx, chunk in enumerate(chunks, start=1):
    out_chunk = TMP_DIR / f"chunk_{idx:03d}.wav"
    synthesize_chunk(chunk, out_chunk)
    chunk_paths.append(out_chunk)

if not chunk_paths:
    raise RuntimeError('No chunk audio generated')

concat_wavs(chunk_paths, OUT_AUDIO)
OUT_CUES.write_text('\n'.join(cue_lines) + '\n', encoding='utf-8')
PY
