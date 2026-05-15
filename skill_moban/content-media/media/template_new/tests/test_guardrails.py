from __future__ import annotations

import tempfile
from pathlib import Path

from conftest import APP_ROOT, BASELINE_SHA_PATH, MISSION_ROOT, OUTPUT_ROOT, WORKSPACE_ROOT, current_hash_lines, output_inventory, output_json, run_build


def test_input_tree_is_unchanged() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert current_hash_lines(MISSION_ROOT) == BASELINE_SHA_PATH.read_text(encoding="utf-8")


def test_output_inventory_is_restricted() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert output_inventory() == {
        "delivery_report.json",
        "frame_index.json",
        "previews/launch_001.mp4",
        "previews/launch_002.mp4",
        "previews/launch_003.mp4",
        "previews/launch_004.mp4",
        "previews/touchdown_001.mp4",
        "previews/touchdown_002.mp4",
        "previews/touchdown_003.mp4",
        "previews/touchdown_004.mp4",
        "previews/tracking_001.mp4",
        "previews/tracking_002.mp4",
        "previews/tracking_003.mp4",
        "previews/tracking_004.mp4",
        "sheets/launch_sheet.jpg",
        "sheets/touchdown_sheet.jpg",
        "sheets/tracking_sheet.jpg",
        "stills/launch_001.png",
        "stills/launch_002.png",
        "stills/launch_003.png",
        "stills/launch_004.png",
        "stills/touchdown_001.png",
        "stills/touchdown_002.png",
        "stills/touchdown_003.png",
        "stills/touchdown_004.png",
        "stills/tracking_001.png",
        "stills/tracking_002.png",
        "stills/tracking_003.png",
        "stills/tracking_004.png",
    }


def test_outputs_have_no_placeholder_or_process_residue() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    frame_index_text = (OUTPUT_ROOT / "frame_index.json").read_text(encoding="utf-8").lower()
    report_text = (OUTPUT_ROOT / "delivery_report.json").read_text(encoding="utf-8").lower()
    for token in ["todo", "tbd", "placeholder", "verifier", "runtime check"]:
        assert token not in frame_index_text
        assert token not in report_text


def test_blank_locator_requests_are_preserved() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    manifest = output_json("frame_index.json")
    blanks = []
    for clip in manifest["clips"]:
        for row in clip["requests"]:
            if row["still_locator"] == "":
                blanks.append(row["request_id"])
                assert (OUTPUT_ROOT / row["still_path"]).is_file()
    assert blanks == ["launch_001", "tracking_001", "touchdown_001"]


def test_build_honors_local_still_helper_contract() -> None:
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        helper_log = temp_root / "helper_calls.log"
        helper_path = temp_root / "fake_media_pick_frame.sh"
        output_root = temp_root / "output"
        default_skill_helper = APP_ROOT / "skills" / "video-frames" / "scripts" / "frame.sh"
        original_helper_bytes: bytes | None = None
        original_helper_mode: int | None = None

        helper_path.write_text(
            f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{helper_log}"

in="${{1:-}}"
shift || true

time=""
index=""
out=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --time)
      time="${{2:-}}"
      shift 2
      ;;
    --index)
      index="${{2:-}}"
      shift 2
      ;;
    --out)
      out="${{2:-}}"
      shift 2
      ;;
    *)
      exit 3
      ;;
  esac
done

mkdir -p "$(dirname "$out")"

if [[ "$index" != "" ]]; then
  "$FFMPEG_BIN" -hide_banner -loglevel error -y -i "$in" -vf "select=eq(n\\,${{index}})" -vframes 1 "$out"
elif [[ "$time" != "" ]]; then
  "$FFMPEG_BIN" -hide_banner -loglevel error -y -ss "$time" -i "$in" -frames:v 1 "$out"
else
  "$FFMPEG_BIN" -hide_banner -loglevel error -y -i "$in" -vf "select=eq(n\\,0)" -vframes 1 "$out"
fi
""",
            encoding="utf-8",
        )
        helper_path.chmod(0o755)

        if default_skill_helper.exists():
            original_helper_bytes = default_skill_helper.read_bytes()
            original_helper_mode = default_skill_helper.stat().st_mode
            default_skill_helper.write_text(helper_path.read_text(encoding="utf-8"), encoding="utf-8")
            default_skill_helper.chmod(0o755)

        try:
            result = run_build(
                output_root=output_root,
                extra_env={"MEDIA_PICK_FRAME_TOOL": str(helper_path)},
            )
            assert result.returncode == 0, result.stderr or result.stdout

            source_text = (WORKSPACE_ROOT / "build_packet.py").read_text(encoding="utf-8")
            assert any(
                marker in source_text
                for marker in (
                    "MEDIA_PICK_FRAME_TOOL",
                    "media-pick-frame",
                    "skills/video-frames",
                )
            )

            if helper_log.exists():
                calls = helper_log.read_text(encoding="utf-8").splitlines()
                assert len(calls) == 12
                assert calls[0].endswith("--out /app/output/stills/launch_001.png") or calls[0].endswith(
                    "--out " + str(output_root / "stills" / "launch_001.png")
                )
                assert "--time 00:00:02.002 --out " in calls[1]
                assert calls[1].endswith("stills/launch_002.png")
                assert "--index 202 --out " in calls[2]
                assert calls[2].endswith("stills/launch_003.png")
                assert "--time 00:00:08.008 --out " in calls[7]
                assert calls[7].endswith("stills/tracking_004.png")
        finally:
            if original_helper_bytes is not None and original_helper_mode is not None:
                default_skill_helper.write_bytes(original_helper_bytes)
                default_skill_helper.chmod(original_helper_mode)
