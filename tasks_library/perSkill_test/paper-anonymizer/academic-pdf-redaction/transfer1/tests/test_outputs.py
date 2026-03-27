import csv
from pathlib import Path

import fitz

IN_DIR = Path("/root")
OUT_DIR = Path("/root/redacted/transfer1")
CSV_FILE = Path("/root/reports/transfer1_matrix.csv")
FILES = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]

TOKENS = {
    "paper1.pdf": ["Yueqian Lin", "Duke University", "arXiv:2509.26542"],
    "paper2.pdf": ["Jiatong Shi", "Carnegie Mellon", "10.21437/Interspeech.2024-33"],
    "paper3.pdf": ["Yueqian Lin", "Duke University", "Equal contribution"],
}


def text(path: Path) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def pages(path: Path) -> int:
    with fitz.open(path) as doc:
        return len(doc)


for fname in FILES:
    original = IN_DIR / fname
    redacted = OUT_DIR / fname
    assert redacted.exists(), f"Missing {redacted}"
    assert pages(original) == pages(redacted), f"Page count changed for {fname}"
    out_text = text(redacted)
    cutoff = out_text.lower().find("references")
    body = out_text if cutoff == -1 else out_text[:cutoff]
    low = body.lower()
    for token in TOKENS[fname]:
        assert token.lower() not in low, f"Token still visible in {fname}: {token}"

assert CSV_FILE.exists(), "Missing transfer1 CSV"
with CSV_FILE.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 3, "CSV must contain 3 data rows"
for row in rows:
    assert row["file"] in FILES
    assert int(row["author_hits"]) >= 1
    assert int(row["total_hits"]) >= int(row["author_hits"])
    assert float(row["retained_ratio"]) >= 0.7
