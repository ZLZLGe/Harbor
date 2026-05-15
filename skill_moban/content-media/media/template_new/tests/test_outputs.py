from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from conftest import (
    MISSION_ROOT,
    OUTPUT_ROOT,
    build_expected_sheet,
    clip_manifest,
    extract_expected_still,
    extract_first_frame,
    image_rmse,
    layout_spec,
    output_json,
    run_build,
    sha256_file,
    shot_requests,
)


def test_build_succeeds() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout


def test_required_outputs_exist_and_decode() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    clip_lookup = {row["clip_id"]: row for row in clip_manifest()["clips"]}

    for request in shot_requests():
        still_path = OUTPUT_ROOT / "stills" / f"{request['request_id']}.png"
        preview_path = OUTPUT_ROOT / "previews" / f"{request['request_id']}.mp4"
        assert still_path.is_file(), still_path
        assert preview_path.is_file(), preview_path
        with Image.open(still_path) as image:
            assert image.size == (
                int(clip_lookup[request["clip_id"]]["width"]),
                int(clip_lookup[request["clip_id"]]["height"]),
            )

    for sheet in layout_spec()["sheets"]:
        path = OUTPUT_ROOT / sheet["output_file"]
        assert path.is_file(), path
        with Image.open(path) as image:
            assert image.size == (sheet["canvas_width"], sheet["canvas_height"])
            assert image.format == "JPEG"

    assert (OUTPUT_ROOT / "frame_index.json").is_file()
    assert (OUTPUT_ROOT / "delivery_report.json").is_file()


def test_manifest_and_report_match_inputs() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    manifest = output_json("frame_index.json")
    report = output_json("delivery_report.json")
    clip_rows = clip_manifest()["clips"]
    requests = shot_requests()

    assert [row["clip_id"] for row in manifest["clips"]] == [row["clip_id"] for row in clip_rows]
    assert report["bundle_id"] == clip_manifest()["bundle_id"]
    assert report["requests_processed"] == len(requests)
    assert report["sheet_count"] == len(layout_spec()["sheets"])

    for clip in manifest["clips"]:
        source_name = next(row["filename"] for row in clip_rows if row["clip_id"] == clip["clip_id"])
        assert clip["source_video"] == source_name
        request_rows = [row for row in requests if row["clip_id"] == clip["clip_id"]]
        assert [row["request_id"] for row in clip["requests"]] == [row["request_id"] for row in request_rows]
        for request_row, manifest_row in zip(request_rows, clip["requests"], strict=True):
            assert manifest_row["slot_name"] == request_row["slot_name"]
            assert manifest_row["still_locator"] == request_row["still_locator"]
            assert float(manifest_row["preview_start_sec"]) == float(request_row["preview_start_sec"])
            assert float(manifest_row["preview_duration_sec"]) == float(request_row["preview_duration_sec"])
            assert str(manifest_row["still_path"]).endswith(f"stills/{request_row['request_id']}.png")
            assert str(manifest_row["preview_path"]).endswith(f"previews/{request_row['request_id']}.mp4")


def test_stills_match_requested_locator_semantics() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    clip_lookup = {row["clip_id"]: row for row in clip_manifest()["clips"]}

    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        for request in shot_requests():
            expected = temp_root / f"{request['request_id']}.png"
            extract_expected_still(
                MISSION_ROOT / "videos" / clip_lookup[request["clip_id"]]["filename"],
                request["still_locator"],
                expected,
            )
            produced = OUTPUT_ROOT / "stills" / f"{request['request_id']}.png"
            assert image_rmse(produced, expected) <= 1.0, request["request_id"]


def test_preview_clips_start_on_requested_frame() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    clip_lookup = {row["clip_id"]: row for row in clip_manifest()["clips"]}

    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        for request in shot_requests():
            expected_frame = temp_root / f"{request['request_id']}_expected.png"
            preview_frame = temp_root / f"{request['request_id']}_preview.png"
            extract_expected_still(
                MISSION_ROOT / "videos" / clip_lookup[request["clip_id"]]["filename"],
                f"--time {request['preview_start_sec']}",
                expected_frame,
            )
            extract_first_frame(OUTPUT_ROOT / "previews" / f"{request['request_id']}.mp4", preview_frame)
            assert image_rmse(expected_frame, preview_frame) <= 8.0, request["request_id"]


def test_contact_sheets_match_layout_spec() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        for sheet in layout_spec()["sheets"]:
            rebuilt = build_expected_sheet(sheet, temp_root / Path(sheet["output_file"]).name)
            assert image_rmse(OUTPUT_ROOT / sheet["output_file"], rebuilt) <= 3.0, sheet["clip_id"]


def test_build_is_deterministic() -> None:
    result_one = run_build()
    assert result_one.returncode == 0, result_one.stderr or result_one.stdout
    first = tempfile.TemporaryDirectory()
    second = tempfile.TemporaryDirectory()
    try:
        first_root = Path(first.name)
        second_root = Path(second.name)
        for path in OUTPUT_ROOT.rglob("*"):
            if path.is_file():
                destination = first_root / path.relative_to(OUTPUT_ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(path.read_bytes())

        result_two = run_build()
        assert result_two.returncode == 0, result_two.stderr or result_two.stdout
        for path in OUTPUT_ROOT.rglob("*"):
            if path.is_file():
                destination = second_root / path.relative_to(OUTPUT_ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(path.read_bytes())

        for relpath in [
            "frame_index.json",
            "delivery_report.json",
            "stills/launch_001.png",
            "stills/tracking_003.png",
            "stills/touchdown_004.png",
            "previews/launch_002.mp4",
            "previews/tracking_001.mp4",
            "sheets/launch_sheet.jpg",
            "sheets/tracking_sheet.jpg",
            "sheets/touchdown_sheet.jpg",
        ]:
            assert sha256_file(first_root / relpath) == sha256_file(second_root / relpath), relpath
    finally:
        first.cleanup()
        second.cleanup()
