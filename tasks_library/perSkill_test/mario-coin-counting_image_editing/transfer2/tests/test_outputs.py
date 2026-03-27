import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path("/root/mario_skill_preview.gif")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def frame_count(path: Path) -> int:
    res = subprocess.run(["identify", str(path)], check=True, capture_output=True, text=True)
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    return len(lines)


def frame_signature(path: Path, index: int) -> str:
    target = f"{path}[{index}]"
    res = subprocess.run(["identify", "-format", "%#", target], check=True, capture_output=True, text=True)
    return res.stdout.strip()


def frame_size(path: Path, index: int) -> tuple[int, int]:
    target = f"{path}[{index}]"
    res = subprocess.run(["identify", "-format", "%w %h", target], check=True, capture_output=True, text=True)
    w, h = res.stdout.strip().split()
    return int(w), int(h)


def build_expected(tmpdir: Path) -> Path:
    f1 = tmpdir / "frame_01.png"
    f2 = tmpdir / "frame_02.png"
    f3 = tmpdir / "frame_03.png"
    f4 = tmpdir / "frame_04.png"
    f5 = tmpdir / "frame_05.png"
    f6 = tmpdir / "frame_06.png"
    expected = tmpdir / "expected.gif"

    run(["convert", "/root/coin.png", "-colorspace", "Gray", "-resize", "80x80!", str(f1)])
    run(["convert", "/root/enemy.png", "-colorspace", "Gray", "-resize", "80x80!", str(f2)])
    run(["convert", "/root/turtle.png", "-colorspace", "Gray", "-resize", "80x80!", str(f3)])
    run(["convert", "/root/coin.png", "-colorspace", "Gray", "-negate", "-resize", "80x80!", str(f4)])
    run(["convert", "/root/enemy.png", "-colorspace", "Gray", "-edge", "1", "-resize", "80x80!", str(f5)])
    run(["convert", "/root/turtle.png", "-colorspace", "Gray", "-blur", "0x1", "-resize", "80x80!", str(f6)])
    run([
        "convert", "-delay", "25", "-loop", "0",
        str(f1), str(f2), str(f3), str(f4), str(f5), str(f6),
        str(expected),
    ])
    return expected


def main() -> int:
    if not OUTPUT.is_file():
        raise AssertionError("missing output gif")

    assert frame_count(OUTPUT) == 6

    with tempfile.TemporaryDirectory(prefix="gif_expected_") as tmp:
        expected = build_expected(Path(tmp))
        assert frame_count(expected) == 6
        for i in range(6):
            assert frame_size(OUTPUT, i) == (80, 80)
            assert frame_size(expected, i) == (80, 80)
            assert frame_signature(OUTPUT, i) == frame_signature(expected, i), f"frame {i} mismatch"
    return 0


if __name__ == "__main__":
    sys.exit(main())
