#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

INPUT_CSV = Path("/root/exhibit_packet/stops.csv")
OUTPUT_ZIP = Path("/root/exhibit-stop-pack.zip")


def synthesize_mp3(spoken_text: str, duration_hint: int, output_path: Path) -> None:
    word_count = max(len(spoken_text.split()), 1)
    target_wpm = int(round(word_count * 60 / duration_hint))
    speed = min(205, max(145, target_wpm))

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "stop.wav"
        subprocess.run(
            [
                "espeak-ng",
                "-v",
                "en-us",
                "-s",
                str(speed),
                "-w",
                str(wav_path),
                spoken_text,
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "4",
                str(output_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main() -> None:
    staging = Path(tempfile.mkdtemp(prefix="exhibit-pack-"))
    manifest = []

    try:
        with INPUT_CSV.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                stop_id = row["stop_id"].strip()
                title = row["title"].strip()
                narration = row["narration"].strip()
                duration_hint = int(row["duration_hint_seconds"])
                spoken_text = f"Stop {stop_id}. {title}. {narration}"
                audio_name = f"{stop_id}.mp3"
                audio_path = staging / audio_name

                synthesize_mp3(spoken_text, duration_hint, audio_path)

                manifest.append(
                    {
                        "stop_id": stop_id,
                        "title": title,
                        "audio_file": audio_name,
                        "duration_hint_seconds": duration_hint,
                        "spoken_text": spoken_text,
                    }
                )

        manifest_path = staging / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        with ZipFile(OUTPUT_ZIP, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(manifest_path, arcname="manifest.json")
            for entry in manifest:
                archive.write(staging / entry["audio_file"], arcname=entry["audio_file"])
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
PY
