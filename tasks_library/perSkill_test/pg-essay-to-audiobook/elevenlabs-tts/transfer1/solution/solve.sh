#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import re
from collections import Counter
from pathlib import Path

INPUT_CSV = Path("/root/data/dubbing_segments.csv")
OUT_CSV = Path("/root/transfer1_voice_plan.csv")
OUT_JSON = Path("/root/transfer1_casting_notes.json")
MAX_CHARS = 1000
VOICE_MAP = {
    "calm_female": "21m00Tcm4TlvDq8ikWAM",
    "soft_female": "EXAVITQu4vr4xnSDxMaL",
    "warm_male": "ErXwobaYiN019PkySvjV",
    "deep_male": "TxGEqnHWrfWFTfGW9XjX",
}


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


rows = []
with INPUT_CSV.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if str(row["publish"]).strip().lower() == "yes":
            rows.append(row)

rows.sort(key=lambda r: int(r["segment_id"]))

out_rows = []
persona_counter: Counter[str] = Counter()
all_voice_ids = set()
total_chunks = 0

for row in rows:
    segment_id = int(row["segment_id"])
    persona = str(row["persona"]).strip()
    voice_id = VOICE_MAP[persona]
    cleaned = clean_text(str(row["text"]))
    chunks = sentence_chunk(cleaned, MAX_CHARS)
    total_chunks += len(chunks)
    persona_counter[persona] += 1
    all_voice_ids.add(voice_id)
    out_rows.append(
        {
            "segment_id": str(segment_id),
            "persona": persona,
            "voice_id": voice_id,
            "char_count": str(len(cleaned)),
            "chunk_count": str(len(chunks)),
            "model_id": "eleven_turbo_v2_5",
        }
    )

with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["segment_id", "persona", "voice_id", "char_count", "chunk_count", "model_id"],
    )
    writer.writeheader()
    writer.writerows(out_rows)

notes = {
    "total_segments": len(out_rows),
    "total_chunks": total_chunks,
    "persona_counts": {k: persona_counter[k] for k in sorted(persona_counter)},
    "voice_ids_used": sorted(all_voice_ids),
}
OUT_JSON.write_text(json.dumps(notes, indent=2), encoding="utf-8")
PY
