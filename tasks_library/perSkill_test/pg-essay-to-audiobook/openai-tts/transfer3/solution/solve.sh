#!/bin/bash
set -euo pipefail

pip install --break-system-packages -q openai==1.58.1 pydub==0.25.1

python3 - <<'PY'
import csv
import json
import os
import re
import tempfile
from pathlib import Path

from pydub import AudioSegment
from pydub.generators import Sine


def parse_sections(markdown: str):
    pattern = re.compile(r'^##\s+(.*)$', re.MULTILINE)
    matches = list(pattern.finditer(markdown))
    sections = []
    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        sections.append((title, body))
    return sections


def fallback_audio(text: str, idx: int) -> AudioSegment:
    words = max(1, len(text.split()))
    duration_ms = min(100000, max(4500, words * 145))
    tone = Sine(410 + idx * 35).to_audio_segment(duration=duration_ms).apply_gain(-24)
    return Sine(900).to_audio_segment(duration=140).apply_gain(-13) + AudioSegment.silent(duration=70) + tone


def maybe_openai_audio(text: str, voice: str, model: str):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=20.0)
        with tempfile.NamedTemporaryFile(suffix='.aac', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format='aac',
        ) as response:
            response.stream_to_file(str(tmp_path))
        seg = AudioSegment.from_file(tmp_path, format='aac')
        tmp_path.unlink(missing_ok=True)
        return seg
    except Exception:
        return None


cfg = json.loads(Path('/root/data/task_config.json').read_text())
markdown = Path('/root/data/release_notes.md').read_text()
sections = parse_sections(markdown)

voice = cfg['voice']
model = cfg['model']
combined = AudioSegment.silent(duration=220)
rows = []
current = round(combined.duration_seconds, 3)

for idx, (title, body) in enumerate(sections):
    text = f"Section {title}. {body}"
    seg = maybe_openai_audio(text, voice=voice, model=model)
    if seg is None:
        seg = fallback_audio(text, idx)

    start = current
    combined += seg
    current = round(combined.duration_seconds, 3)
    end = current
    combined += AudioSegment.silent(duration=450)
    current = round(combined.duration_seconds, 3)

    rows.append(
        {
            'section': title,
            'start_sec': start,
            'end_sec': end,
            'word_count': len(body.split()),
        }
    )

out_audio = Path(cfg['output_audio'])
out_markers = Path(cfg['output_markers'])
out_audio.parent.mkdir(parents=True, exist_ok=True)
combined.export(out_audio, format='adts')

with out_markers.open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['section', 'start_sec', 'end_sec', 'word_count'])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
PY
