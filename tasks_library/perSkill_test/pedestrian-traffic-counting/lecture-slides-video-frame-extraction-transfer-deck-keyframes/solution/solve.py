#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


ROOT = Path("/app/lectures")
RECORDINGS_DIR = ROOT / "recordings"
KEYFRAMES_DIR = ROOT / "keyframes"
OUTPUT_JSON = ROOT / "slide_keyframes.json"
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def extract_keyframes(video_path: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "slide_%03d.jpg"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-skip_frame",
            "nokey",
            "-i",
            str(video_path),
            "-vsync",
            "vfr",
            str(pattern),
        ],
        check=True,
    )
    return sorted(output_dir.glob("slide_*.jpg"))


def main() -> None:
    videos = sorted(
        path for path in RECORDINGS_DIR.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )

    manifest: list[dict[str, object]] = []
    for video_path in videos:
        frame_dir = KEYFRAMES_DIR / video_path.stem
        frames = extract_keyframes(video_path, frame_dir)
        for index, frame_path in enumerate(frames, start=1):
            manifest.append(
                {
                    "video_filename": video_path.name,
                    "sequence_number": index,
                    "frame_filename": str(frame_path.relative_to(ROOT)),
                }
            )

    OUTPUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
