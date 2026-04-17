#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import re
import socket
import subprocess
import tempfile
from pathlib import Path

from gtts import gTTS

DATA_DIR = Path("/root/data")
OUT_AUDIO = Path("/root/casefile_narration.mp3")
OUT_SEGMENTS = Path("/root/casefile_segments.json")
MAX_CHARS = 190


def chunk_text(text: str, max_chars: int) -> list[str]:
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


def has_network() -> bool:
    try:
        with socket.create_connection(("translate.google.com", 443), timeout=1.5):
            return True
    except OSError:
        return False


def synth_chunk(text: str, out_mp3: Path, state: dict[str, int | bool]) -> None:
    if state["online"]:
        try:
            gTTS(text=text, lang="en", slow=False, timeout=3).save(str(out_mp3))
            state["gtts_chunks"] += 1
            return
        except Exception:
            state["online"] = False

    wav_path = out_mp3.with_suffix(".wav")
    subprocess.run(["python3", "/root/tools/offline_tts.py", "--text", text, "--output", str(wav_path)], check=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "5",
            str(out_mp3),
        ],
        check=True,
    )
    wav_path.unlink(missing_ok=True)


def concat_mp3(inputs: list[Path], output: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as file_list:
        list_path = Path(file_list.name)
        for item in inputs:
            escaped = str(item).replace("'", "'\\''")
            file_list.write(f"file '{escaped}'\n")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(output),
        ],
        check=True,
    )
    list_path.unlink(missing_ok=True)


phase_order = json.loads((DATA_DIR / "phase_order.json").read_text(encoding="utf-8"))["order"]
phase_rank = {phase: idx for idx, phase in enumerate(phase_order)}

rows = []
with (DATA_DIR / "casefile_fragments.csv").open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for idx, row in enumerate(reader):
        rows.append(
            {
                "case_id": row["case_id"].strip(),
                "phase": row["phase"].strip(),
                "note": re.sub(r"\s+", " ", row["note"].strip()),
                "_idx": idx,
            }
        )

rows.sort(key=lambda r: (r["case_id"], phase_rank.get(r["phase"], len(phase_rank)), r["_idx"]))

case_ids = sorted({r["case_id"] for r in rows})
chars_per_case = {cid: 0 for cid in case_ids}
segments: list[str] = []
current_case = None

for row in rows:
    cid = row["case_id"]
    phase = row["phase"]
    note = row["note"]

    if cid != current_case:
        segments.append(f"Case {cid} summary.")
        current_case = cid

    sentence = f"Case {cid}, {phase} phase: {note}."
    segments.append(sentence)
    chars_per_case[cid] += len(note)

narration = " ".join(segments)
chunks = chunk_text(narration, MAX_CHARS)
if not chunks:
    raise RuntimeError("No narration chunks created")

state: dict[str, int | bool] = {"online": has_network(), "gtts_chunks": 0}
audio_parts: list[Path] = []

with tempfile.TemporaryDirectory(prefix="transfer3_chunks_") as tmp:
    tmp_dir = Path(tmp)
    for idx, chunk in enumerate(chunks, start=1):
        out_mp3 = tmp_dir / f"chunk_{idx:04d}.mp3"
        synth_chunk(chunk, out_mp3, state)
        audio_parts.append(out_mp3)

    concat_mp3(audio_parts, OUT_AUDIO)

provider = "offline-fallback"
if state["gtts_chunks"] == len(chunks):
    provider = "gtts"
elif state["gtts_chunks"] > 0:
    provider = "hybrid"

payload = {
    "provider": provider,
    "case_ids": case_ids,
    "phase_order": phase_order,
    "segment_count": len(rows),
    "chars_per_case": chars_per_case,
    "total_chunks": len(chunks),
    "gtts_chunk_count": state["gtts_chunks"],
}
OUT_SEGMENTS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
