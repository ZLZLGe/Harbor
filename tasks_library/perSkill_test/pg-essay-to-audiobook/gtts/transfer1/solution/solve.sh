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
OUT_AUDIO = Path("/root/briefing_digest.mp3")
OUT_INDEX = Path("/root/briefing_index.json")
MAX_CHARS = 210

BRIEFINGS = {
    "alpha": DATA_DIR / "briefing_alpha.md",
    "beta": DATA_DIR / "briefing_beta.md",
    "gamma": DATA_DIR / "briefing_gamma.md",
}


def parse_markdown(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = "Untitled Briefing"
    body_parts: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.*)$", stripped)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            if title == "Untitled Briefing":
                title = heading_text
            else:
                body_parts.append(heading_text)
            continue
        stripped = re.sub(r"^-\s+", "", stripped)
        body_parts.append(stripped)
    body = " ".join(body_parts)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"\[\d+\]", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return title, body


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


playlist = json.loads((DATA_DIR / "playlist_order.json").read_text(encoding="utf-8"))
order = playlist.get("order", [])
if not order:
    raise RuntimeError("playlist_order.json is missing non-empty 'order'")

state: dict[str, int | bool] = {"online": has_network(), "gtts_chunks": 0}
ordered_titles: list[str] = []
ordered_ids: list[str] = []
chunk_counts: dict[str, int] = {}
total_input_chars = 0
all_chunks: list[Path] = []

with tempfile.TemporaryDirectory(prefix="transfer1_chunks_") as tmp:
    tmp_dir = Path(tmp)
    chunk_counter = 0

    for briefing_id in order:
        if briefing_id not in BRIEFINGS:
            raise RuntimeError(f"Unknown briefing id in playlist: {briefing_id}")

        title, body = parse_markdown(BRIEFINGS[briefing_id])
        ordered_ids.append(briefing_id)
        ordered_titles.append(title)
        total_input_chars += len(body)

        text = f"Briefing: {title}. {body}"
        pieces = chunk_text(text, MAX_CHARS)
        chunk_counts[briefing_id] = len(pieces)

        for piece in pieces:
            chunk_counter += 1
            out_mp3 = tmp_dir / f"chunk_{chunk_counter:04d}.mp3"
            synth_chunk(piece, out_mp3, state)
            all_chunks.append(out_mp3)

    if not all_chunks:
        raise RuntimeError("No chunks were generated")

    concat_mp3(all_chunks, OUT_AUDIO)

provider = "offline-fallback"
if state["gtts_chunks"] == len(all_chunks):
    provider = "gtts"
elif state["gtts_chunks"] > 0:
    provider = "hybrid"

index_payload = {
    "provider": provider,
    "ordered_ids": ordered_ids,
    "ordered_titles": ordered_titles,
    "chunk_counts": chunk_counts,
    "total_chunks": len(all_chunks),
    "total_input_chars": total_input_chars,
    "gtts_chunk_count": state["gtts_chunks"],
}
OUT_INDEX.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
PY
