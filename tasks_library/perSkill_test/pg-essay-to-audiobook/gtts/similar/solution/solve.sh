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

CHAPTERS = [
    ("Do Things that Don't Scale", Path("/root/data/do-things.html")),
    ("Founder Mode", Path("/root/data/founder-mode.html")),
]
MAX_CHARS = 260
OUT_AUDIO = Path("/root/audiobook.mp3")
OUT_MANIFEST = Path("/root/audiobook_manifest.json")


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


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
    subprocess.run(
        ["python3", "/root/tools/offline_tts.py", "--text", text, "--output", str(wav_path)],
        check=True,
    )
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
    if not inputs:
        raise RuntimeError("No audio chunks generated")

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as list_file:
        list_path = Path(list_file.name)
        for item in inputs:
            escaped = str(item).replace("'", "'\\''")
            list_file.write(f"file '{escaped}'\n")

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


state: dict[str, int | bool] = {
    "online": has_network(),
    "gtts_chunks": 0,
}

all_chunks: list[Path] = []
chapter_titles: list[str] = []
total_clean_chars = 0

with tempfile.TemporaryDirectory(prefix="similar_chunks_") as tmp:
    tmp_dir = Path(tmp)

    chunk_counter = 0
    for title, chapter_file in CHAPTERS:
        raw_html = chapter_file.read_text(encoding="utf-8")
        cleaned = clean_text(html_to_text(raw_html))
        chapter_titles.append(title)
        total_clean_chars += len(cleaned)

        chapter_text = f"Chapter: {title}. {cleaned}"
        pieces = chunk_text(chapter_text, MAX_CHARS)

        for piece in pieces:
            chunk_counter += 1
            out_mp3 = tmp_dir / f"chunk_{chunk_counter:04d}.mp3"
            synth_chunk(piece, out_mp3, state)
            all_chunks.append(out_mp3)

    concat_mp3(all_chunks, OUT_AUDIO)

provider = "offline-fallback"
if state["gtts_chunks"] == len(all_chunks) and all_chunks:
    provider = "gtts"
elif state["gtts_chunks"] > 0:
    provider = "hybrid"

manifest = {
    "provider": provider,
    "chapter_titles": chapter_titles,
    "chapter_count": len(chapter_titles),
    "total_chunks": len(all_chunks),
    "total_clean_chars": total_clean_chars,
    "gtts_chunk_count": state["gtts_chunks"],
}
OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY
