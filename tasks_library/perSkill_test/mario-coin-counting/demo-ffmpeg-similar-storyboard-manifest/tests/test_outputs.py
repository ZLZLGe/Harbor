import subprocess
from pathlib import Path

import pandas as pd
from PIL import Image

VIDEO_FILE = "/root/demo-clip.mp4"
OUTPUT_FILE = Path("/root/storyboard_manifest.csv")
FRAME_DIR = Path("/root/storyboard_frames")


def count_video_iframes() -> int:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=pict_type",
            "-of",
            "csv=p=0",
            VIDEO_FILE,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return sum(1 for line in result.stdout.splitlines() if line.strip().startswith("I"))


class TestStoryboardOutputs:
    def test_frame_sequence_exists(self):
        frames = sorted(FRAME_DIR.glob("scene_*.png"))
        expected_count = count_video_iframes()

        assert FRAME_DIR.is_dir()
        assert expected_count > 0
        assert len(frames) == expected_count

        for index, frame_path in enumerate(frames, start=1):
            assert frame_path.name == f"scene_{index:03d}.png"

    def test_manifest_matches_extracted_frames(self):
        assert OUTPUT_FILE.is_file()

        frames = sorted(FRAME_DIR.glob("scene_*.png"))
        manifest = pd.read_csv(OUTPUT_FILE)

        assert list(manifest.columns) == [
            "frame_path",
            "sequence",
            "width",
            "height",
            "file_size_bytes",
        ]
        assert len(manifest) == len(frames) == count_video_iframes()
        assert manifest["sequence"].tolist() == list(range(1, len(frames) + 1))

        for row, frame_path in zip(manifest.itertuples(index=False), frames):
            assert row.frame_path == str(frame_path)
            with Image.open(frame_path) as image:
                width, height = image.size
            assert row.width == width
            assert row.height == height
            assert row.file_size_bytes == frame_path.stat().st_size
