#!/bin/bash
set -euo pipefail

pip install --break-system-packages -q openai==1.58.1 pydub==0.25.1

python3 - <<'PY'
import json
import os
import tempfile
from pathlib import Path

from pydub import AudioSegment
from pydub.generators import Sine


def fallback_audio(text: str, idx: int) -> AudioSegment:
    words = max(1, len(text.split()))
    duration_ms = min(90000, max(5000, words * 150))
    tone_hz = 390 + (idx * 40)
    tone = Sine(tone_hz).to_audio_segment(duration=duration_ms).apply_gain(-23)
    return Sine(980).to_audio_segment(duration=180).apply_gain(-12) + AudioSegment.silent(duration=90) + tone


def maybe_openai_audio(text: str, voice: str, model: str):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=20.0)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format='wav',
        ) as response:
            response.stream_to_file(str(tmp_path))
        seg = AudioSegment.from_file(tmp_path, format='wav')
        tmp_path.unlink(missing_ok=True)
        return seg
    except Exception:
        return None


cfg = json.loads(Path('/root/data/task_config.json').read_text())
updates = json.loads(Path('/root/data/incident_updates.json').read_text())['updates']

voice = cfg['voice']
model = cfg['model']
compiled = AudioSegment.silent(duration=250)
segments = []
current_sec = round(compiled.duration_seconds, 3)

for idx, item in enumerate(updates):
    prompt = (
        f"Update {item['update_code']}. Priority {item['priority']}. "
        f"Title: {item['title']}. {item['body']}"
    )
    seg = maybe_openai_audio(prompt, voice=voice, model=model)
    if seg is None:
        seg = fallback_audio(prompt, idx)

    start = current_sec
    compiled += seg
    current_sec = round(compiled.duration_seconds, 3)
    end = current_sec
    compiled += AudioSegment.silent(duration=700)
    current_sec = round(compiled.duration_seconds, 3)

    segments.append(
        {
            'update_code': item['update_code'],
            'priority': item['priority'],
            'start_sec': start,
            'end_sec': end,
        }
    )

out_audio = Path(cfg['output_audio'])
out_cues = Path(cfg['output_cues'])
out_audio.parent.mkdir(parents=True, exist_ok=True)
compiled.export(out_audio, format='wav')

report = {
    'voice': voice,
    'model': model,
    'total_duration_sec': round(compiled.duration_seconds, 3),
    'segments': segments,
}
out_cues.write_text(json.dumps(report, indent=2))
PY
