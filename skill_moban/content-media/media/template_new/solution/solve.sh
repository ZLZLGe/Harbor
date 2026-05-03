#!/bin/bash
set -euo pipefail

python3 <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

from PIL import Image


INPUT_DIR = Path(os.environ.get("MEDIA_PICK_INPUT_DIR", "/root/media_pick/input"))
OUTPUT_DIR = Path(os.environ.get("MEDIA_PICK_OUTPUT_DIR", "/root/media_pick/output"))
STILL_DIR = OUTPUT_DIR / "stills"
PREVIEW_DIR = OUTPUT_DIR / "previews"
SHEET_DIR = OUTPUT_DIR / "sheets"
SKILL_FRAME = Path(os.environ.get("MEDIA_PICK_FRAME_TOOL", "/usr/local/bin/media-pick-frame"))
SKILL_FRAME_FALLBACK = Path("/root/.codex/skills/video-frames/scripts/frame.sh")
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def run_capture(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def ensure_dirs() -> None:
    for path in [OUTPUT_DIR, STILL_DIR, PREVIEW_DIR, SHEET_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_manifest() -> dict:
    return json.loads((INPUT_DIR / "clip_manifest.json").read_text(encoding="utf-8"))


def load_layout() -> dict:
    return json.loads((INPUT_DIR / "layout_spec.json").read_text(encoding="utf-8"))


def load_requests() -> list[dict[str, str]]:
    with (INPUT_DIR / "shot_requests.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_still_locator(locator: str) -> tuple[str, str]:
    locator = locator.strip()
    if not locator:
        return "default", ""
    if locator.startswith("--time "):
        return "time", locator.removeprefix("--time ").strip()
    if locator.startswith("--index "):
        return "index", locator.removeprefix("--index ").strip()
    raise ValueError(f"Unsupported still_locator: {locator}")


def extract_still(video_path: Path, request: dict[str, str], out_path: Path) -> None:
    mode, value = parse_still_locator(request["still_locator"])
    frame_tool = SKILL_FRAME if SKILL_FRAME.exists() else SKILL_FRAME_FALLBACK
    if frame_tool.exists():
        cmd = [str(frame_tool), str(video_path)]
        if mode == "time":
            cmd.extend(["--time", value])
        elif mode == "index":
            cmd.extend(["--index", value])
        cmd.extend(["--out", str(out_path)])
        run(cmd)
        return

    if mode == "time":
        run([
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            value,
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(out_path),
        ])
    elif mode == "index":
        run([
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"select=eq(n\\,{value})",
            "-vframes",
            "1",
            str(out_path),
        ])
    else:
        run([
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "select=eq(n\\,0)",
            "-vframes",
            "1",
            str(out_path),
        ])


def extract_preview(video_path: Path, request: dict[str, str], out_path: Path) -> None:
    run([
        FFMPEG_BIN,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        request["preview_start_sec"],
        "-i",
        str(video_path),
        "-t",
        request["preview_duration_sec"],
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ])


def build_sheet(still_paths: list[Path], clip: dict, layout: dict, out_path: Path) -> None:
    cols = int(layout["grid_columns"])
    rows = int(layout["grid_rows_per_clip"])
    width = int(clip["width"])
    height = int(clip["height"])
    canvas = Image.new("RGB", (cols * width, rows * height), tuple(layout["background_rgb"]))
    for idx, still_path in enumerate(still_paths):
        with Image.open(still_path) as img:
            tile = img.convert("RGB")
            left = (idx % cols) * width
            top = (idx // cols) * height
            canvas.paste(tile, (left, top))
    canvas.save(out_path, format="JPEG", quality=int(layout["jpeg_quality"]))


def main() -> None:
    ensure_dirs()
    manifest = load_manifest()
    layout = load_layout()
    requests = load_requests()
    clips = {clip["clip_id"]: clip for clip in manifest["clips"]}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for request in requests:
        grouped[request["clip_id"]].append(request)

    frame_index = {"clips": []}
    files_created: list[str] = []
    videos_processed: list[dict[str, object]] = []

    for clip in manifest["clips"]:
        clip_id = clip["clip_id"]
        video_path = INPUT_DIR / "videos" / clip["filename"]
        requests_for_clip = grouped[clip_id]
        clip_entries: list[dict[str, object]] = []
        still_paths: list[Path] = []

        for request in requests_for_clip:
            still_path = STILL_DIR / f"{request['request_id']}.png"
            preview_path = PREVIEW_DIR / f"{request['request_id']}.mp4"
            extract_still(video_path, request, still_path)
            extract_preview(video_path, request, preview_path)
            still_paths.append(still_path)

            with Image.open(still_path) as img:
                width, height = img.size

            clip_entries.append({
                "request_id": request["request_id"],
                "slot_name": request["slot_name"],
                "still_locator": request["still_locator"],
                "preview_start_sec": float(request["preview_start_sec"]),
                "preview_duration_sec": float(request["preview_duration_sec"]),
                "still_path": f"stills/{request['request_id']}.png",
                "preview_path": f"previews/{request['request_id']}.mp4",
                "width": width,
                "height": height,
                "sha256": sha256(still_path),
            })

            files_created.append(f"stills/{request['request_id']}.png")
            files_created.append(f"previews/{request['request_id']}.mp4")

        sheet_path = SHEET_DIR / f"{clip_id}_sheet.jpg"
        build_sheet(still_paths, clip, layout, sheet_path)
        files_created.append(f"sheets/{clip_id}_sheet.jpg")

        frame_index["clips"].append({
            "clip_id": clip_id,
            "source_video": clip["filename"],
            "sheet_path": f"sheets/{clip_id}_sheet.jpg",
            "requests": clip_entries,
        })
        videos_processed.append({
            "clip_id": clip_id,
            "source_video": clip["filename"],
            "request_count": len(requests_for_clip),
            "sheet_path": f"sheets/{clip_id}_sheet.jpg",
            "status": "pass",
        })

    files_created.extend(["frame_index.json", "delivery_report.json"])
    (OUTPUT_DIR / "frame_index.json").write_text(json.dumps(frame_index, indent=2), encoding="utf-8")
    delivery_report = {
        "files_created": files_created,
        "videos_processed": videos_processed,
        "requests_processed": len(requests),
        "sheet_count": len(manifest["clips"]),
        "issues": [],
        "notes": [
            "All pickup requests were processed.",
            "Still frames kept native pixel dimensions.",
            "Contact sheets follow the per-clip request order."
        ],
    }
    (OUTPUT_DIR / "delivery_report.json").write_text(json.dumps(delivery_report, indent=2), encoding="utf-8")


main()
PY
