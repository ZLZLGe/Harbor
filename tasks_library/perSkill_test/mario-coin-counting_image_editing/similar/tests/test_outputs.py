import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path("/root/mario_keyframe_strip.png")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def image_size(path: Path) -> tuple[int, int]:
    res = subprocess.run(["identify", "-format", "%w %h", str(path)], check=True, capture_output=True, text=True)
    w, h = res.stdout.strip().split()
    return int(w), int(h)


def image_signature(path: Path) -> str:
    res = subprocess.run(["identify", "-format", "%#", str(path)], check=True, capture_output=True, text=True)
    return res.stdout.strip()


def build_expected(tmpdir: Path) -> Path:
    p1 = tmpdir / "sim_panel_01.png"
    p2 = tmpdir / "sim_panel_02.png"
    p3 = tmpdir / "sim_panel_03.png"
    p4 = tmpdir / "sim_panel_04.png"
    expected = tmpdir / "expected_strip.png"

    run(["convert", "/root/coin.png", "-colorspace", "Gray", "-resize", "64x64!", str(p1)])
    run(["convert", "/root/enemy.png", "-colorspace", "Gray", "-resize", "64x64!", str(p2)])
    run(["convert", "/root/turtle.png", "-colorspace", "Gray", "-resize", "64x64!", str(p3)])
    run(["convert", "/root/coin.png", "-colorspace", "Gray", "-negate", "-resize", "64x64!", str(p4)])
    run(["convert", str(p1), str(p2), str(p3), str(p4), "+append", str(expected)])
    return expected


def main() -> int:
    if not OUTPUT.is_file():
        raise AssertionError("missing output strip")
    assert image_size(OUTPUT) == (256, 64)

    with tempfile.TemporaryDirectory(prefix="similar_expected_") as tmp:
        expected = build_expected(Path(tmp))
        assert image_signature(OUTPUT) == image_signature(expected), "strip content mismatch"
    return 0


if __name__ == "__main__":
    sys.exit(main())
