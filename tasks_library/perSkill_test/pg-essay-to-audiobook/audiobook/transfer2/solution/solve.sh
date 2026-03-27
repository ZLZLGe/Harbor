#!/bin/bash
set -euo pipefail

python3 - << 'PY'
import json
import re
import subprocess
import wave
from pathlib import Path

OUT_AUDIO = Path('/root/transfer2_training_digest.wav')
OUT_JSON = Path('/root/transfer2_digest.json')
TMP_DIR = Path('/tmp/transfer2_chunks')
TMP_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def chunk_text(text: str, max_chars: int = 160) -> list[str]:
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
for line in Path('/root/data/call_snippets.jsonl').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line:
        continue
    rows.append(json.loads(line))

kept = [r for r in rows if bool(r.get('publish')) and int(r.get('priority', 0)) >= 2]
kept.sort(key=lambda r: (int(r['session_id']), str(r.get('speaker', ''))))

sentences = []
for r in kept:
    sid = int(r['session_id'])
    speaker = str(r.get('speaker', '')).strip()
    text = clean_text(str(r.get('text', '')))
    sentences.append(f"Segment {sid} - {speaker}: {text}.")

narration = ' '.join(sentences).strip()
chunks = chunk_text(narration, max_chars=160)

chunk_paths: list[Path] = []
for idx, chunk in enumerate(chunks, start=1):
    out_chunk = TMP_DIR / f"chunk_{idx:03d}.wav"
    synthesize_chunk(chunk, out_chunk)
    chunk_paths.append(out_chunk)

if not chunk_paths:
    raise RuntimeError('No chunk audio generated')

concat_wavs(chunk_paths, OUT_AUDIO)

report = {
    'included_session_ids': sorted({int(r['session_id']) for r in kept}),
    'segment_count': len(sentences),
    'chunk_count': len(chunks),
    'total_chars': len(narration),
}
OUT_JSON.write_text(json.dumps(report, indent=2), encoding='utf-8')
PY
