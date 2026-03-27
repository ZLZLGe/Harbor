import csv
from pathlib import Path

from pypdf import PdfReader

OUT_DIR = Path("/root/output/transfer2_pages")
MANIFEST = Path("/root/reports/transfer2_split_manifest.csv")

assert MANIFEST.exists(), "Missing split manifest CSV"
with MANIFEST.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 4, "Manifest must have 4 rows"
for i, row in enumerate(rows, start=1):
    expected_name = f"page_{i:03d}.pdf"
    assert int(row["page_index"]) == i
    assert row["output_file"] == expected_name
    assert int(row["char_count"]) > 0

    pdf_path = OUT_DIR / expected_name
    assert pdf_path.exists(), f"Missing split file {pdf_path}"
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 1, f"Split file {expected_name} must contain exactly one page"
    assert len((reader.pages[0].extract_text() or "").strip()) > 20
