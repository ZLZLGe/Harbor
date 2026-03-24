import csv
import hashlib
import io
import re
import subprocess
from pathlib import Path

OUTPUT_FILE = Path("/root/frame_hash_index.tsv")
VIDEO_FILE = Path("/root/archive-camera.mp4")
FRAME_DIR = Path("/root/archive_keyframes")


def count_video_iframes() -> int:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-skip_frame",
            "nokey",
            "-show_entries",
            "frame=pict_type",
            "-of",
            "csv=p=0",
            str(VIDEO_FILE),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return sum(1 for line in result.stdout.splitlines() if line.strip().startswith("I"))


class TestFrameHashIndex:
    def test_extracted_frames_match_video_keyframes(self):
        frames = sorted(FRAME_DIR.glob("archive_*.png"))
        expected_count = count_video_iframes()

        assert FRAME_DIR.is_dir()
        assert expected_count > 0
        assert len(frames) == expected_count

        for sequence, frame_path in enumerate(frames, start=1):
            assert frame_path.name == f"archive_{sequence:04d}.png"

    def test_tsv_matches_extracted_frames_and_hashes(self):
        assert OUTPUT_FILE.is_file()

        raw_output = OUTPUT_FILE.read_bytes()
        assert raw_output.endswith(b"\n")

        reader = csv.DictReader(io.StringIO(raw_output.decode("utf-8")), delimiter="\t")
        assert reader.fieldnames == ["frame_path", "sequence", "sha256"]

        rows = list(reader)
        frames = sorted(FRAME_DIR.glob("archive_*.png"))

        assert len(rows) == len(frames) == count_video_iframes()

        for sequence, (row, frame_path) in enumerate(zip(rows, frames), start=1):
            assert row["frame_path"] == str(frame_path)
            assert row["sequence"] == str(sequence)
            assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
            assert row["sha256"] == hashlib.sha256(frame_path.read_bytes()).hexdigest()
