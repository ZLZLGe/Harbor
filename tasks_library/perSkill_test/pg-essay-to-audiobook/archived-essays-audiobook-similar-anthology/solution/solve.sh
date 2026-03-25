#!/bin/bash
set -euo pipefail

python3 <<'PY'
import subprocess
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

INPUT_DIR = Path("/root/archive_snapshots")
ORDER_FILE = INPUT_DIR / "reading_order.txt"
SCRIPT_PATH = Path("/root/founder-anthology-script.txt")
OUTPUT_MP3 = Path("/root/founder-anthology-audiobook.mp3")

NOISE_SELECTORS = [
    "nav",
    "aside",
    "footer",
    "form",
    "script",
    "style",
    ".noise-block",
    ".newsletter",
    ".left-rail",
    ".right-rail",
    ".top-strip",
    ".site-header",
    ".site-footer",
    ".related-links",
]

BODY_SELECTORS = [
    "article[data-main-content='true']",
    "article.essay-body",
    "section[data-story='primary']",
    ".story-body",
    "article",
    "main",
]


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def load_reading_order():
    chapters = []
    for raw_line in ORDER_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        number, filename, title = line.split("|", 2)
        chapters.append(
            {
                "number": int(number),
                "filename": filename,
                "title": title,
            }
        )
    return chapters


def extract_body(html_path: Path) -> list[str]:
    soup = BeautifulSoup(html_path.read_text(), "html.parser")

    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    container = None
    for selector in BODY_SELECTORS:
        node = soup.select_one(selector)
        if node:
            container = node
            break
    if container is None:
        raise RuntimeError(f"Could not find essay body in {html_path}")

    paragraphs = []
    for element in container.find_all("p"):
        text = normalize_whitespace(element.get_text(" ", strip=True))
        if text:
            paragraphs.append(text)

    if not paragraphs:
        raise RuntimeError(f"No paragraphs extracted from {html_path}")

    return paragraphs


def build_script(chapters):
    script_sections = []
    audio_sections = []

    for chapter in chapters:
        paragraphs = extract_body(INPUT_DIR / chapter["filename"])
        heading = f"Chapter {chapter['number']}: {chapter['title']}"
        opening = f"Opening: Archived essay {chapter['number']}, {chapter['title']}."

        script_sections.append("\n".join([heading, opening, "", *paragraphs]))

        spoken_heading = f"Chapter {chapter['number']}. {chapter['title']}."
        spoken_opening = f"Archived essay {chapter['number']}, {chapter['title']}."
        audio_sections.append("\n".join([spoken_heading, spoken_opening, "", *paragraphs]))

    SCRIPT_PATH.write_text("\n\n".join(script_sections).strip() + "\n")
    return audio_sections


def synthesize(audio_sections):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        list_path = tmp / "concat.txt"
        wav_paths = []

        for idx, section_text in enumerate(audio_sections, start=1):
            text_path = tmp / f"chapter_{idx}.txt"
            wav_path = tmp / f"chapter_{idx}.wav"
            silence_path = tmp / f"pause_{idx}.wav"

            text_path.write_text(section_text)
            subprocess.run(
                [
                    "espeak-ng",
                    "-v",
                    "en-us",
                    "-s",
                    "145",
                    "-f",
                    str(text_path),
                    "-w",
                    str(wav_path),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=22050:cl=mono",
                    "-t",
                    "0.6",
                    str(silence_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            wav_paths.extend([wav_path, silence_path])

        list_path.write_text("".join(f"file '{path}'\n" for path in wav_paths))

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-ar",
                "22050",
                "-ac",
                "1",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "4",
                str(OUTPUT_MP3),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


chapters = load_reading_order()
audio_sections = build_script(chapters)
synthesize(audio_sections)
PY
