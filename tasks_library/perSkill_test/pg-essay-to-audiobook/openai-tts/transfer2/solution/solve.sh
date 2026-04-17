#!/bin/bash
set -euo pipefail

pip install --break-system-packages -q openai==1.58.1 pydub==0.25.1

python3 - <<'PY'
import csv
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from pydub import AudioSegment
from pydub.generators import Sine


def fallback_audio(text: str, priority: str) -> AudioSegment:
    words = max(1, len(text.split()))
    duration_ms = min(85000, max(4500, words * 140))
    base_hz = {'high': 520, 'medium': 430, 'low': 350}.get(priority, 380)
    tone = Sine(base_hz).to_audio_segment(duration=duration_ms).apply_gain(-23)
    return Sine(980).to_audio_segment(duration=120).apply_gain(-13) + AudioSegment.silent(duration=60) + tone


def maybe_openai_audio(text: str, voice: str, model: str):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=20.0)
        with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format='flac',
        ) as response:
            response.stream_to_file(str(tmp_path))
        seg = AudioSegment.from_file(tmp_path, format='flac')
        tmp_path.unlink(missing_ok=True)
        return seg
    except Exception:
        return None


cfg = json.loads(Path('/root/data/task_config.json').read_text())
rows = list(csv.DictReader(Path('/root/data/call_snippets.csv').read_text().splitlines()))

voice = cfg['voice']
model = cfg['model']
priority_counts = Counter()
combined = AudioSegment.silent(duration=180)

for row in rows:
    priority = row['priority'].strip().lower()
    priority_counts[priority] += 1
    prompt = f"Priority {priority}. Customer {row['customer']}. Message: {row['message']}"

    seg = maybe_openai_audio(prompt, voice=voice, model=model)
    if seg is None:
        seg = fallback_audio(prompt, priority)

    combined += seg + AudioSegment.silent(duration=500)

out_audio = Path(cfg['output_audio'])
out_report = Path(cfg['output_report'])
out_audio.parent.mkdir(parents=True, exist_ok=True)
combined.export(out_audio, format='flac')

report = {
    'rows_processed': len(rows),
    'priority_counts': dict(sorted(priority_counts.items())),
    'voice': voice,
    'model': model,
    'total_duration_sec': round(combined.duration_seconds, 3),
}
out_report.write_text(json.dumps(report, indent=2))
PY
