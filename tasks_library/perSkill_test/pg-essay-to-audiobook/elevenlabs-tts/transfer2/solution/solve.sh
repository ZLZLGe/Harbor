#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
from pathlib import Path

INPUT_PATH = Path("/root/data/raw_queue.jsonl")
OUT_JSON = Path("/root/transfer2_queue_normalized.json")
OUT_REJECTED = Path("/root/transfer2_rejected_ids.txt")
MAX_CHARS = 1500
ALLOWED_VOICES = {
    "21m00Tcm4TlvDq8ikWAM",
    "EXAVITQu4vr4xnSDxMaL",
    "ErXwobaYiN019PkySvjV",
    "TxGEqnHWrfWFTfGW9XjX",
}
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"


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


def to_unit_float(value) -> float:
    try:
        f = float(value)
    except Exception:
        return 0.5
    return max(0.0, min(1.0, f))


source_rows = []
for line in INPUT_PATH.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line:
        source_rows.append(json.loads(line))

requests = []
rejected_ids = []
accepted_jobs = 0

for row in source_rows:
    job_id = str(row.get("id", "")).strip()
    enabled = bool(row.get("enabled"))
    cleaned = clean_text(str(row.get("text", "")))

    if not enabled or not cleaned:
        if job_id:
            rejected_ids.append(job_id)
        continue

    accepted_jobs += 1
    voice_id = str(row.get("voice_id", "")).strip()
    if voice_id not in ALLOWED_VOICES:
        voice_id = DEFAULT_VOICE

    stability = to_unit_float(row.get("stability"))
    similarity = to_unit_float(row.get("similarity_boost"))

    chunks = sentence_chunk(cleaned, MAX_CHARS)
    for idx, chunk in enumerate(chunks, start=1):
        requests.append(
            {
                "request_id": f"{job_id}-{idx}",
                "url": f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                "headers": {
                    "xi-api-key": "${ELEVENLABS_API_KEY}",
                    "Content-Type": "application/json",
                },
                "body": {
                    "text": chunk,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity,
                    },
                },
            }
        )

result = {
    "requests": requests,
    "meta": {
        "source_jobs": len(source_rows),
        "accepted_jobs": accepted_jobs,
        "rejected_jobs": len(source_rows) - accepted_jobs,
    },
}
OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
OUT_REJECTED.write_text("\n".join(sorted(rejected_ids)) + "\n", encoding="utf-8")
PY
