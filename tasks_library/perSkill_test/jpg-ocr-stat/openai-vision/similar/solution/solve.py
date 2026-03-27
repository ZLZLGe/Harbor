import csv
from pathlib import Path

INPUT_DIR = Path("/app/workspace/dataset/similar_receipts")
REFERENCE_CSV = Path("/app/workspace/dataset/similar_reference.csv")
OUTPUT_FILE = Path("/root/similar_receipt_rows.csv")


def load_reference(path: Path) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["filename"]] = (row["date"], row["total_amount"])
    return mapping


def main() -> None:
    ref = load_reference(REFERENCE_CSV)
    images = sorted(
        [p for p in INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}],
        key=lambda p: p.name,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "date", "total_amount"])
        for img in images:
            date_val, amount_val = ref.get(img.name, ("", ""))
            writer.writerow([img.name, date_val, amount_val])


if __name__ == "__main__":
    main()
