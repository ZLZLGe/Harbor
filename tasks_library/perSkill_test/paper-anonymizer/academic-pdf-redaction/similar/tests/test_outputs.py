import json
from pathlib import Path

import fitz

INPUT_DIR = Path("/root")
OUTPUT_DIR = Path("/root/redacted/similar")
REPORT = Path("/root/reports/similar_redaction_report.json")
FILES = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]

SENSITIVE = {
    "paper1.pdf": ["Yueqian Lin", "Duke University", "arXiv:2509.26542"],
    "paper2.pdf": ["Jiatong Shi", "Carnegie Mellon", "10.21437/Interspeech.2024-33"],
    "paper3.pdf": ["Yueqian Lin", "Duke University", "Equal contribution"],
}

SELF_CITATION = {
    "paper1.pdf": "Lin et al., 2025c",
    "paper2.pdf": "Muskits",
}


def extract_text(path: Path) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def page_count(path: Path) -> int:
    with fitz.open(path) as doc:
        return len(doc)


for fname in FILES:
    in_pdf = INPUT_DIR / fname
    out_pdf = OUTPUT_DIR / fname
    assert out_pdf.exists(), f"Missing output: {out_pdf}"
    assert page_count(in_pdf) == page_count(out_pdf), f"Page count changed for {fname}"

    text = extract_text(out_pdf)
    cutoff = text.lower().find("references")
    body = text if cutoff == -1 else text[:cutoff]
    body_lower = body.lower()

    for token in SENSITIVE[fname]:
        assert token.lower() not in body_lower, f"Sensitive token still visible in body of {fname}: {token}"

for fname, token in SELF_CITATION.items():
    out_pdf = OUTPUT_DIR / fname
    text = extract_text(out_pdf).lower()
    assert token.lower() in text, f"Reference content removed unexpectedly in {fname}: {token}"

assert REPORT.exists(), "Missing JSON report"
rows = json.loads(REPORT.read_text(encoding="utf-8"))
assert isinstance(rows, list) and len(rows) == 3, "Report must have 3 rows"
for row in rows:
    assert row["file"] in FILES
    assert row["redaction_hits"] > 0
    assert row["retained_ratio"] >= 0.7
