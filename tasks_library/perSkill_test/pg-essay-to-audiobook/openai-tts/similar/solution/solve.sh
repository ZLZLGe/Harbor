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


def fallback_audio(text: str) -> AudioSegment:
    words = max(1, len(text.split()))
    duration_ms = min(120000, max(7000, words * 170))
    base = Sine(440).to_audio_segment(duration=duration_ms).apply_gain(-24)
    marker = Sine(880).to_audio_segment(duration=220).apply_gain(-14)
    return marker + AudioSegment.silent(duration=120) + base


def maybe_openai_audio(text: str, voice: str, model: str):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=20.0)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
        ) as response:
            response.stream_to_file(str(tmp_path))
        seg = AudioSegment.from_file(tmp_path, format="mp3")
        tmp_path.unlink(missing_ok=True)
        return seg
    except Exception:
        return None


cfg = json.loads(Path("/root/data/task_config.json").read_text())
source = json.loads(Path("/root/data/essay_fragments.json").read_text())

voice = cfg["voice"]
model = cfg["model"]
combined = AudioSegment.silent(duration=300)
manifest_chapters = []

for chapter in source["chapters"]:
    title = chapter["title"]
    text = chapter["text"].strip()
    prompt = f"Chapter {title}. {text}"
    segment = maybe_openai_audio(prompt, voice=voice, model=model)
    if segment is None:
        segment = fallback_audio(prompt)

    manifest_chapters.append(
        {
            "chapter_id": chapter["chapter_id"],
            "title": title,
            "duration_sec": round(segment.duration_seconds, 3),
            "char_count": len(text),
        }
    )
    combined += segment + AudioSegment.silent(duration=800)

out_audio = Path(cfg["output_audio"])
out_manifest = Path(cfg["output_manifest"])
out_audio.parent.mkdir(parents=True, exist_ok=True)
combined.export(out_audio, format="mp3")

manifest = {
    "voice": voice,
    "model": model,
    "chapters": manifest_chapters,
    "total_duration_sec": round(combined.duration_seconds, 3),
}
out_manifest.write_text(json.dumps(manifest, indent=2))
PY
