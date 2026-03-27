import csv
import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path("/root/mario_image_audit.csv")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def metric_row(name: str, image: Path) -> list[str]:
    wh = subprocess.run(["identify", "-format", "%w,%h", str(image)], check=True, capture_output=True, text=True).stdout.strip()
    mean_txt = subprocess.run(["identify", "-format", "%[fx:mean*255]", str(image)], check=True, capture_output=True, text=True).stdout.strip()
    mean = float(mean_txt)
    width, height = wh.split(",")
    return [name, width, height, f"{mean:.2f}"]


def build_expected_rows(tmpdir: Path) -> list[list[str]]:
    coin = tmpdir / "audit_coin.png"
    enemy = tmpdir / "audit_enemy.png"
    turtle = tmpdir / "audit_turtle.png"

    run(["convert", "/root/coin.png", "-colorspace", "Gray", "-resize", "48x48!", str(coin)])
    run(["convert", "/root/enemy.png", "-colorspace", "Gray", "-resize", "48x48!", "-contrast", str(enemy)])
    run(["convert", "/root/turtle.png", "-colorspace", "Gray", "-resize", "48x48!", "-blur", "0x1", str(turtle)])

    rows = [["asset", "width", "height", "mean_gray"]]
    rows.append(metric_row("coin", coin))
    rows.append(metric_row("enemy", enemy))
    rows.append(metric_row("turtle", turtle))
    return rows


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [row for row in csv.reader(f)]


def main() -> int:
    if not OUTPUT.is_file():
        raise AssertionError("missing audit csv")

    with tempfile.TemporaryDirectory(prefix="audit_expected_") as tmp:
        expected_rows = build_expected_rows(Path(tmp))
        output_rows = read_csv_rows(OUTPUT)
        assert output_rows == expected_rows
    return 0


if __name__ == "__main__":
    sys.exit(main())
