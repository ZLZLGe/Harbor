#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import socket
import subprocess
import tempfile
from pathlib import Path

from gtts import gTTS

DATA_DIR = Path("/root/data")
OUT_AUDIO = Path("/root/call_recap.mp3")
OUT_REPORT = Path("/root/call_recap_report.json")
MAX_CHARS = 170


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


severity_order = json.loads((DATA_DIR / "severity_order.json").read_text(encoding="utf-8"))["order"]
rank = {name: idx for idx, name in enumerate(severity_order)}

items = []
for idx, raw in enumerate((DATA_DIR / "call_snippets.jsonl").read_text(encoding="utf-8").splitlines()):
    line = raw.strip()
    if not line:
        continue
    payload = json.loads(line)
    payload["_idx"] = idx
    payload["text"] = re.sub(r"\s+", " ", payload["text"]).strip()
    items.append(payload)

items.sort(key=lambda x: (rank.get(x["severity"], len(rank)), x["_idx"]))

narration_sentences: list[str] = []
chars_by_severity: dict[str, int] = {name: 0 for name in severity_order}

for sev in severity_order:
    group = [it for it in items if it["severity"] == sev]
    if not group:
        continue
    narration_sentences.append(f"Priority {sev} updates.")
    for entry in group:
        sentence = f"{entry['speaker']} from {entry['case_id']} reports: {entry['text']}."
        narration_sentences.append(sentence)
        chars_by_severity[sev] += len(entry["text"])

narration_text = " ".join(narration_sentences)
chunks = chunk_text(narration_text, MAX_CHARS)
if not chunks:
    raise RuntimeError("No narration chunks created")

state: dict[str, int | bool] = {"online": has_network(), "gtts_chunks": 0}
audio_parts: list[Path] = []

with tempfile.TemporaryDirectory(prefix="transfer2_chunks_") as tmp:
    tmp_dir = Path(tmp)
    for idx, text in enumerate(chunks, start=1):
        out_mp3 = tmp_dir / f"chunk_{idx:04d}.mp3"
        synth_chunk(text, out_mp3, state)
        audio_parts.append(out_mp3)

    concat_mp3(audio_parts, OUT_AUDIO)

provider = "offline-fallback"
if state["gtts_chunks"] == len(chunks):
    provider = "gtts"
elif state["gtts_chunks"] > 0:
    provider = "hybrid"

report = {
    "provider": provider,
    "severity_order": severity_order,
    "item_count": len(items),
    "unique_cases": sorted({entry["case_id"] for entry in items}),
    "chars_by_severity": chars_by_severity,
    "total_chunks": len(chunks),
    "gtts_chunk_count": state["gtts_chunks"],
}
OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
PY
