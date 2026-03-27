import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path("/root/mario_icon_atlas.png")


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
    coin = tmpdir / "coin_norm.png"
    enemy = tmpdir / "enemy_norm.png"
    turtle = tmpdir / "turtle_norm.png"
    expected = tmpdir / "expected_atlas.png"

    run(["convert", "/root/coin.png", "-colorspace", "Gray", "-resize", "64x64!", str(coin)])
    run(["convert", "/root/enemy.png", "-colorspace", "Gray", "-flip", "-resize", "64x64!", str(enemy)])
    run(["convert", "/root/turtle.png", "-colorspace", "Gray", "-flop", "-resize", "64x64!", str(turtle)])
    run(["convert", str(coin), str(enemy), str(turtle), "+append", str(expected)])
    return expected


def main() -> int:
    if not OUTPUT.is_file():
        raise AssertionError("missing output atlas")
    assert image_size(OUTPUT) == (192, 64)

    with tempfile.TemporaryDirectory(prefix="atlas_expected_") as tmp:
        expected = build_expected(Path(tmp))
        assert image_signature(OUTPUT) == image_signature(expected), "atlas content mismatch"
    return 0


if __name__ == "__main__":
    sys.exit(main())
